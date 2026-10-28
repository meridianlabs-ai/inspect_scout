"""Message IDs for transcripts imported from trace formats."""

import json
from collections.abc import Sequence

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
    should carry the same ID:

    - A message with an ID from the source keeps it (when `source_ids` is True,
      a non-None `id` is taken to be one; the importer sets the rest to None).
    - Any other message takes the ID of an earlier message with the same
      content, unless that ID is already in the same conversation.
    - Otherwise it is the message's first appearance, and its ID is the call's
      ID plus the message's position in that call (the output's position is
      `len(input)`).
    """

    def __init__(self, source_ids: bool = False) -> None:
        """Create the assigner for one trace.

        Args:
            source_ids: Whether the importer set `id` to the source's own
                message ID (or None where it has none) on the messages it
                passes in. When False, every message gets an assigned ID.
        """
        self._source_ids = source_ids
        self._ids_by_content: dict[str, list[str]] = {}
        self._assigned: set[str] = set()

    def apply(self, event: ModelEvent, call_id: str) -> None:
        """Assign IDs to a model call's input and output messages.

        Args:
            event: The model call.
            call_id: The source's ID for the call (e.g. span or run ID).
        """
        conversation = self.apply_messages(event.input, call_id)
        output = event.output
        if isinstance(output, ModelOutput) and output.choices:
            self._assign(output.message, f"{call_id}-{len(event.input)}", conversation)

    def apply_messages(self, messages: Sequence[ChatMessage], call_id: str) -> set[str]:
        """Assign IDs to a conversation's messages.

        Args:
            messages: The conversation.
            call_id: The source's ID for the call or record the messages
                came from.

        Returns:
            The IDs in the conversation.
        """
        conversation: set[str] = set()
        for index, message in enumerate(messages):
            self._assign(message, f"{call_id}-{index}", conversation)
        return conversation

    def _assign(
        self, message: ChatMessage, first_id: str, conversation: set[str]
    ) -> None:
        content = _content_hash(message)
        ids = self._ids_by_content.setdefault(content, [])
        if self._source_ids and message.id is not None:
            if message.id not in ids:
                ids.append(message.id)
        else:
            earlier = next((i for i in ids if i not in conversation), None)
            if earlier is None:
                earlier = self._unique(first_id)
                ids.append(earlier)
            message.id = earlier
        self._assigned.add(message.id)
        conversation.add(message.id)

    def _unique(self, candidate: str) -> str:
        # Positional IDs only collide when the source reuses a call ID.
        unique = candidate
        suffix = 1
        while unique in self._assigned:
            unique = f"{candidate}.{suffix}"
            suffix += 1
        return unique


def _content_hash(message: ChatMessage) -> str:
    data = message.model_dump(exclude=_UNMATCHED_FIELDS, exclude_none=True)
    return mmh3.hash_bytes(json.dumps(data, sort_keys=True).encode()).hex()
