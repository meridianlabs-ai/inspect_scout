"""Message IDs for transcripts imported from trace formats."""

import json
from collections.abc import Sequence
from dataclasses import dataclass, field

import mmh3
from inspect_ai.event import ModelEvent
from inspect_ai.model import ChatMessage

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
      to different contents (an edited copy), each later content takes
      `edit_id(source ID, content)`, moved to a `.1` suffix if a real ID
      equals it.
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
        # Each `_Message` is one message and holds every copy of it, so
        # renaming it relabels them all. The indexes hold `_Message` objects,
        # so they stay valid through a rename: `_first_positions` is a prefix
        # tree of content hashes; `_by_content` lists messages per content
        # hash; `_by_id` maps current IDs to messages; `_by_source` maps
        # (source ID, content hash) to the message the source ID names there.
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
        reply = event.output.message if event.output.choices else None
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
                message, f"{call_id}-{index}", positions, conversation, is_input=True
            )
        if reply is not None:
            self._place(
                reply,
                f"{call_id}-{len(messages)}",
                positions,
                conversation,
                is_input=False,
            )

    def _place(
        self,
        message: ChatMessage,
        first_id: str,
        positions: dict[str, "_Position"],
        conversation: "_Conversation",
        *,
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
        # A message with a positional ID can be one the source names later.
        adopt = earlier if earlier is not None and not earlier.from_source else None
        holder = self._by_id.get(source_id)
        if holder is not None and holder.allocated and holder is not adopt:
            # An ID this assigner made up that happens to equal the source's.
            self._rename(holder, self._unique(holder.id))

        identity = self._by_source.get((source_id, content))
        if identity is None:
            if adopt is not None:
                identity = adopt
                identity.from_source = True
            else:
                identity = self._new(source_id, content, from_source=True)
            if self._source_id_taken(source_id, identity):
                identity.edited = True
                self._rename(identity, self._unique(edit_id(source_id, content)))
            else:
                self._rename(identity, source_id)
            self._by_source[(source_id, content)] = identity
        return identity

    def _source_id_taken(self, source_id: str, by: "_Message") -> bool:
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
    edited: bool = False

    @property
    def allocated(self) -> bool:
        """Whether the ID was made up here (positional, or an edit's)."""
        return not self.from_source or self.edited

    def add_copy(self, message: ChatMessage) -> None:
        self.copies.append(message)
        self.label(message)

    def label(self, message: ChatMessage) -> None:
        message.id = self.id


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


def edit_id(source_id: str, content: str) -> str:
    """ID of an edited copy: content the source gives `source_id` after another.

    The ID is the source ID plus the full 128-bit hash of the source ID and the
    content, so it depends only on those two; different contents getting the
    same hash is not a practical concern. Callers add a `.1`, `.2`, ... suffix
    only when a real ID in the trace happens to equal it.

    Args:
        source_id: The source's ID for the message.
        content: A hash or key of the edited copy's content.
    """
    digest = mmh3.hash_bytes(json.dumps([source_id, content]).encode()).hex()
    return f"{source_id}.{digest}"


def _content_hash(message: ChatMessage) -> str:
    data = message.model_dump(mode="json", exclude=_UNMATCHED_FIELDS, exclude_none=True)
    return mmh3.hash_bytes(json.dumps(data, sort_keys=True).encode()).hex()
