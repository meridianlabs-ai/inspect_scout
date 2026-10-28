"""Message IDs for transcripts imported from trace formats."""

import json
from collections.abc import Sequence
from dataclasses import dataclass, field

import mmh3
from inspect_ai.event import ModelEvent
from inspect_ai.model import ChatMessage, ModelOutput

# Fields that can differ between a model's output message and the copy of it
# sent back as input on the next call.
_UNMATCHED_FIELDS = {"id", "source", "model", "metadata"}


class TraceMessageIds:
    """Assigns message IDs across the model calls of one imported trace.

    Trace formats re-send the conversation on every model call, so the importer
    builds a separate copy of each message per call. Every copy of a message
    should carry the same ID, and different messages different IDs:

    - A message with an ID from the source keeps it (when `source_ids` is True,
      a non-None `id` is taken to be one; the importer sets the rest to None).
      Copies already given another ID take it too. If the source gives one ID
      to different contents (an edited copy), each later content takes the
      ID plus a suffix, with the source ID in `metadata["derived_from"]`.
    - A model's output is a new message.
    - An input message is the one at the same position in an earlier call
      that sent the same messages before it. Failing that, it is an earlier
      message with the same content that isn't already in this conversation.
    - Otherwise it is the message's first appearance, and its ID is the call's
      ID plus the message's position in that call (the output's position is
      `len(input)`). Such an ID moves aside if the source later uses it.
    """

    def __init__(self, source_ids: bool = False) -> None:
        """Create the assigner for one trace.

        Args:
            source_ids: Whether the importer set `id` to the source's own
                message ID (or None where it has none) on the messages it
                passes in. When False, every message gets an assigned ID.
        """
        self._source_ids = source_ids
        self._first_positions: dict[str, _Position] = {}
        self._by_content: dict[str, list[_Message]] = {}
        self._by_id: dict[str, _Message] = {}
        self._by_source: dict[tuple[str, str], _Message] = {}
        self._suffixes: dict[str, int] = {}

    def apply(self, event: ModelEvent, call_id: str) -> None:
        """Assign IDs to a model call's input and output messages.

        Args:
            event: The model call.
            call_id: The source's ID for the call (e.g. span or run ID).
        """
        output = event.output
        reply = (
            output.message
            if isinstance(output, ModelOutput) and output.choices
            else None
        )
        self._apply(event.input, call_id, reply)

    def apply_messages(self, messages: Sequence[ChatMessage], call_id: str) -> None:
        """Assign IDs to a conversation's messages.

        Args:
            messages: The conversation.
            call_id: The source's ID for the call or record the messages
                came from.
        """
        self._apply(messages, call_id, None)

    def _apply(
        self,
        messages: Sequence[ChatMessage],
        call_id: str,
        reply: ChatMessage | None,
    ) -> None:
        conversation = _Conversation()
        positions = self._first_positions
        for index, message in enumerate(messages):
            positions = self._place(
                message, f"{call_id}-{index}", positions, conversation, True
            )
        if reply is not None:
            self._place(
                reply, f"{call_id}-{len(messages)}", positions, conversation, False
            )

    def _place(
        self,
        message: ChatMessage,
        first_id: str,
        positions: dict[str, "_Position"],
        conversation: "_Conversation",
        is_input: bool,
    ) -> dict[str, "_Position"]:
        """Identify one message; return the positions that can follow it."""
        content = _content_hash(message)
        position = positions.get(content)
        earlier: _Message | None = None
        if is_input:
            if position is not None and position.message not in conversation:
                earlier = position.message
            else:
                earlier = conversation.first_absent(
                    content, self._by_content.get(content, [])
                )

        if self._source_ids and message.id is not None:
            identity = self._from_source(message.id, content, earlier)
        elif earlier is not None:
            identity = earlier
        else:
            identity = self._new(self._unique(first_id), content, from_source=False)

        identity.add_copy(message)
        conversation.add(identity)
        if position is None:
            position = positions[content] = _Position(identity)
        else:
            position.message = identity
        return position.next

    def _from_source(
        self, source_id: str, content: str, earlier: "_Message | None"
    ) -> "_Message":
        holder = self._by_id.get(source_id)
        if holder is not None and not holder.from_source and holder is not earlier:
            # A positional ID that happens to equal the source's ID.
            self._rename(holder, self._unique(source_id))
        identity = self._by_source.get((source_id, content))
        adopt = earlier is not None and not earlier.from_source
        if identity is None and earlier is not None and adopt:
            identity = earlier
            identity.from_source = True
            if self._source_id_taken(source_id, earlier):
                identity.derived_from = [source_id]
                self._rename(identity, self._unique(source_id))
            else:
                self._rename(identity, source_id)
        elif identity is None:
            if self._source_id_taken(source_id, None):
                identity = self._new(self._unique(source_id), content, True)
                identity.derived_from = [source_id]
            else:
                identity = self._new(source_id, content, True)
        elif earlier is not None and adopt and earlier is not identity:
            # Copies given a positional ID before the source named them.
            earlier.from_source = True
            earlier.derived_from = identity.derived_from
            self._rename(earlier, identity.id)
        self._by_source[(source_id, content)] = identity
        return identity

    def _source_id_taken(self, source_id: str, by: "_Message | None") -> bool:
        holder = self._by_id.get(source_id)
        return holder is not None and holder is not by

    def _new(self, message_id: str, content: str, from_source: bool) -> "_Message":
        identity = _Message(message_id, from_source)
        self._by_id.setdefault(message_id, identity)
        self._by_content.setdefault(content, []).append(identity)
        return identity

    def _rename(self, identity: "_Message", message_id: str) -> None:
        if self._by_id.get(identity.id) is identity:
            del self._by_id[identity.id]
        identity.id = message_id
        for copy in identity.copies:
            identity.label(copy)
        self._by_id.setdefault(message_id, identity)

    def _unique(self, candidate: str) -> str:
        if candidate not in self._by_id:
            return candidate
        suffix = self._suffixes.get(candidate, 1)
        while f"{candidate}.{suffix}" in self._by_id:
            suffix += 1
        self._suffixes[candidate] = suffix + 1
        return f"{candidate}.{suffix}"


@dataclass(eq=False)
class _Message:
    """One message of the trace, and every copy of it."""

    id: str
    from_source: bool
    copies: list[ChatMessage] = field(default_factory=list)
    derived_from: list[str] | None = None

    def add_copy(self, message: ChatMessage) -> None:
        self.copies.append(message)
        self.label(message)

    def label(self, message: ChatMessage) -> None:
        message.id = self.id
        if self.derived_from:
            message.metadata = {
                **(message.metadata or {}),
                "derived_from": self.derived_from,
            }


@dataclass(eq=False)
class _Position:
    """The message most recently sent after a given sequence of messages."""

    message: _Message
    next: dict[str, "_Position"] = field(default_factory=dict)


class _Conversation:
    """The messages of one conversation, as they are identified."""

    def __init__(self) -> None:
        self._messages: set[_Message] = set()
        self._skipped: dict[str, int] = {}

    def __contains__(self, identity: _Message) -> bool:
        return identity in self._messages

    def add(self, identity: _Message) -> None:
        self._messages.add(identity)

    def first_absent(self, content: str, candidates: list[_Message]) -> _Message | None:
        # Candidates once found in the conversation stay in it, so each
        # content's scan resumes where the last one stopped.
        index = self._skipped.get(content, 0)
        while index < len(candidates) and candidates[index] in self._messages:
            index += 1
        self._skipped[content] = index
        return candidates[index] if index < len(candidates) else None


def _content_hash(message: ChatMessage) -> str:
    data = message.model_dump(mode="json", exclude=_UNMATCHED_FIELDS, exclude_none=True)
    return mmh3.hash_bytes(json.dumps(data, sort_keys=True).encode()).hex()
