import pytest
from inspect_ai.model import ChatMessage, ChatMessageUser
from inspect_scout._scanner.extract import (
    EVENT_MARKER_KEY,
    MessagesPreprocessor,
    message_numbering,
)


@pytest.mark.asyncio
async def test_event_message_numbered_as_e_and_skips_m() -> None:
    render, extract_refs = message_numbering()
    text = await render(
        [
            ChatMessageUser(content="hi", id="u1"),
            ChatMessageUser(
                content="SCORE (match): value=C\n",
                id="ev-1",
                metadata={EVENT_MARKER_KEY: True},
            ),
            ChatMessageUser(content="bye", id="u2"),
        ]
    )
    assert "[M1] USER:\nhi" in text
    assert "[E1] SCORE (match): value=C" in text
    assert "[M2] USER:\nbye" in text


@pytest.mark.asyncio
async def test_event_counter_continues_across_render_calls() -> None:
    # segment_messages renders per-segment via separate calls; ordinals must
    # accumulate globally so [E#] stays unique across segments.
    def event(id: str) -> ChatMessageUser:
        return ChatMessageUser(
            content="SCORE: x\n", id=id, metadata={EVENT_MARKER_KEY: True}
        )

    render, extract_refs = message_numbering()
    await render([event("ev-1")])
    await render([ChatMessageUser(content="hi", id="u1")])
    text = await render([event("ev-2")])
    assert "[E2] SCORE: x" in text
    refs = extract_refs("[E1] [E2] [M1]")
    assert {(r.type, r.id) for r in refs} == {
        ("event", "ev-1"),
        ("event", "ev-2"),
        ("message", "u1"),
    }


@pytest.mark.asyncio
async def test_transform_does_not_see_event_messages() -> None:
    # A custom preprocessor.transform is written against real conversation
    # turns; synthetic event entries must bypass it untouched.
    seen: list[str] = []

    async def transform(messages: list[ChatMessage]) -> list[ChatMessage]:
        seen.extend(m.text for m in messages)
        return [ChatMessageUser(content=m.text.upper(), id=m.id) for m in messages]

    render, _ = message_numbering(
        preprocessor=MessagesPreprocessor(transform=transform)
    )
    text = await render(
        [
            ChatMessageUser(content="hi", id="u1"),
            ChatMessageUser(
                content="SCORE: x\n", id="ev-1", metadata={EVENT_MARKER_KEY: True}
            ),
        ]
    )
    assert seen == ["hi"]
    assert "[M1] USER:\nHI" in text
    assert "[E1] SCORE: x" in text
