import pytest
from inspect_ai.model import ChatMessage, ChatMessageUser
from inspect_scout._scanner.extract import (
    EVENT_MARKER_KEY,
    MessagesPreprocessor,
    message_numbering,
)


def _event(id: str) -> ChatMessageUser:
    return ChatMessageUser(
        content="SCORE: x\n", id=id, metadata={EVENT_MARKER_KEY: True}
    )


@pytest.mark.asyncio
async def test_event_messages_numbered_on_their_own_counter() -> None:
    """[E#] skips [M#] and, like it, accumulates across per-segment render calls."""
    render, extract_refs = message_numbering()
    first = await render(
        [
            ChatMessageUser(content="hi", id="u1"),
            _event("ev-1"),
            ChatMessageUser(content="bye", id="u2"),
        ]
    )
    second = await render([_event("ev-2")])
    assert "[M1] USER:\nhi" in first
    assert "[E1] SCORE: x" in first
    assert "[M2] USER:\nbye" in first
    assert "[E2] SCORE: x" in second
    refs = extract_refs("[E1] [E2] [M2]")
    assert {(r.type, r.id) for r in refs} == {
        ("event", "ev-1"),
        ("event", "ev-2"),
        ("message", "u2"),
    }


@pytest.mark.asyncio
async def test_transform_does_not_see_event_messages() -> None:
    seen: list[str] = []

    async def transform(messages: list[ChatMessage]) -> list[ChatMessage]:
        seen.extend(m.text for m in messages)
        return [ChatMessageUser(content=m.text.upper(), id=m.id) for m in messages]

    render, _ = message_numbering(
        preprocessor=MessagesPreprocessor(transform=transform)
    )
    text = await render([ChatMessageUser(content="hi", id="u1"), _event("ev-1")])
    assert seen == ["hi"]
    assert "[M1] USER:\nHI" in text
    assert "[E1] SCORE: x" in text
