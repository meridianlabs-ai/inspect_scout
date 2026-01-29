"""Stable message ID generation based on content hash."""

import json
from collections.abc import Sequence

import mmh3
from inspect_ai.event._model import ModelEvent
from inspect_ai.model import ChatMessage
from inspect_ai.model._model_output import ModelOutput
from shortuuid import uuid as shortuuid


class MessageIdManager:
    """Generate stable message IDs based on content hash.

    Messages with identical content receive the same ID within a transcript,
    enabling cross-event message identity tracking. This is useful when an
    agent makes multiple LLM calls where subsequent calls include previous
    messages in the conversation history.
    """

    def __init__(self) -> None:
        self._hash_to_ids: dict[str, list[str]] = {}

    def get_id(self, message: ChatMessage, conversation: list[ChatMessage]) -> str:
        """Get stable ID for message, avoiding duplicates within conversation.

        Args:
            message: The message to get an ID for.
            conversation: The conversation context (messages already processed).

        Returns:
            A stable ID for the message based on its content hash.
        """
        msg_hash = self._hash_message(message)
        existing_ids = self._hash_to_ids.get(msg_hash, [])
        conversation_ids = {m.id for m in conversation if m.id}

        # Reuse existing ID if not already in this conversation
        for existing_id in existing_ids:
            if existing_id not in conversation_ids:
                return existing_id

        # Generate new ID
        new_id = shortuuid()
        self._hash_to_ids.setdefault(msg_hash, []).append(new_id)
        return new_id

    def _hash_message(self, message: ChatMessage) -> str:
        """Hash message content using mmh3 (fast 128-bit hash).

        Args:
            message: The message to hash.

        Returns:
            Hex string of the 128-bit hash.
        """
        msg_dict = message.model_dump(exclude={"id"}, exclude_none=True)
        json_str = json.dumps(msg_dict, sort_keys=True)
        # Use mmh3 128-bit hash, return hex string
        hash_bytes = mmh3.hash_bytes(json_str.encode())
        return hash_bytes.hex()

    def apply_ids(self, messages: Sequence[ChatMessage]) -> None:
        """Apply stable IDs to a list of messages in place.

        Args:
            messages: The messages to assign IDs to.
        """
        processed: list[ChatMessage] = []
        for msg in messages:
            msg.id = self.get_id(msg, processed)
            processed.append(msg)


def apply_message_ids_to_event(event: ModelEvent, id_manager: MessageIdManager) -> None:
    """Apply stable IDs to all messages in a ModelEvent.

    Args:
        event: The ModelEvent to apply IDs to.
        id_manager: The MessageIdManager to use for ID generation.
    """
    # Apply to input messages
    input_messages = list(event.input)
    id_manager.apply_ids(input_messages)

    # Apply to output message if present (check choices to avoid IndexError)
    output = event.output
    if isinstance(output, ModelOutput) and output.choices:
        output.message.id = id_manager.get_id(output.message, input_messages)
