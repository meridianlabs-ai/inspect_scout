import pytest
from inspect_ai.model import ChatMessageUser
from inspect_scout._scanner.extract import EVENT_MARKER_KEY, message_numbering


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
async def test_event_reference_resolves_as_event() -> None:
    render, extract_refs = message_numbering()
    await render(
        [
            ChatMessageUser(
                content="ERROR:\nboom\n",
                id="ev-42",
                metadata={EVENT_MARKER_KEY: True},
            )
        ]
    )
    refs = extract_refs("see [E1]")
    assert len(refs) == 1
    assert refs[0].type == "event"
    assert refs[0].id == "ev-42"
