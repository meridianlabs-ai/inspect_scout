"""Checks shared by the importer tests for message IDs and `messages_from`."""

from typing import Any

from inspect_ai.event import ModelEvent
from inspect_ai.model import ChatMessage
from inspect_scout import Transcript


def conversation(event: ModelEvent) -> list[ChatMessage]:
    """A model call's input followed by its output message."""
    if event.output.choices:
        return [*event.input, event.output.message]
    return list(event.input)


def assert_message_ids_consistent(transcript: Transcript) -> None:
    """Check that message IDs and `messages_from` agree with the events.

    - `messages_from` names model events in the transcript, and the last
      one's conversation is in `messages`.
    - Every message has an ID, unique within its conversation.
    - An ID names the same message wherever it appears, in any model call
      or in `messages`.
    """
    model_events = [e for e in transcript.events if isinstance(e, ModelEvent)]
    by_uuid = {e.uuid: e for e in model_events}
    assert transcript.messages_from, "messages_from is not set"
    for uuid in transcript.messages_from:
        assert uuid in by_uuid, f"messages_from names no model event: {uuid}"
    last = ids(conversation(by_uuid[transcript.messages_from[-1]]))
    if len(transcript.messages_from) == 1:
        # Messages added after the call may follow it.
        assert ids(transcript.messages[: len(last)]) == last
    else:
        # Earlier segments are spliced in front of it.
        assert ids(transcript.messages[-len(last) :]) == last

    content_by_id: dict[str, dict[str, Any]] = {}
    for messages in [transcript.messages, *map(conversation, model_events)]:
        message_ids = ids(messages)
        assert None not in message_ids
        assert len(set(message_ids)) == len(message_ids), (
            f"repeated ID in a conversation: {message_ids}"
        )
        for message in messages:
            assert message.id is not None
            content = message.model_dump(
                exclude={"id", "source", "model", "metadata"}, exclude_none=True
            )
            assert content_by_id.setdefault(message.id, content) == content, (
                f"ID {message.id} names two different messages"
            )


def ids(messages: list[ChatMessage]) -> list[str | None]:
    """The messages' IDs."""
    return [m.id for m in messages]
