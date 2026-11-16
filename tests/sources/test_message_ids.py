"""Message IDs assigned across an imported trace's model calls."""

import time

import pytest
from inspect_ai.model import ChatMessageAssistant, ChatMessageUser, Content, ContentText
from inspect_scout.sources._message_ids import TraceMessageIds


@pytest.mark.slow
def test_many_equal_messages_in_one_conversation_take_linear_time() -> None:
    # A gross-regression budget, not a benchmark: this takes about 0.3s on a
    # laptop, while the quadratic matching it replaced took over 10s.
    messages = [ChatMessageUser(content="same") for _ in range(50_000)]

    start = time.perf_counter()
    TraceMessageIds().apply_messages(messages, "call")
    elapsed = time.perf_counter() - start

    assert elapsed < 3
    assert len({m.id for m in messages}) == len(messages)


def test_edit_ids_depend_only_on_source_id_and_content() -> None:
    # These two edits' IDs clashed when edit IDs kept 32 bits of the hash.
    edits = ["edit 76998", "edit 90928"]

    def edit_ids(order: list[str]) -> dict[str, str | None]:
        assigner = TraceMessageIds(source_ids=True)
        messages = [
            ChatMessageUser(content=text, id="human-1") for text in ["original", *order]
        ]
        for index, message in enumerate(messages):
            assigner.apply_messages([message], f"call-{index}")
        return {message.text: message.id for message in messages[1:]}

    forward = edit_ids(edits)
    assert edit_ids(edits[::-1]) == forward
    assert len(set(forward.values())) == 2


@pytest.mark.parametrize(
    ("resent", "same_message"),
    [
        pytest.param("reply", True, id="plain-text"),
        pytest.param([ContentText(text="reply")], True, id="one-text-block"),
        pytest.param([ContentText(text="changed")], False, id="edited-text-block"),
        pytest.param(
            [ContentText(text="re"), ContentText(text="ply")],
            False,
            id="two-text-blocks",
        ),
    ],
)
def test_a_resent_reply_keeps_its_source_id_when_its_text_form_differs(
    resent: str | list[Content], same_message: bool
) -> None:
    # Some providers' replies are plain text as output and one text block when
    # sent back as input.
    reply = ChatMessageAssistant(content="reply", id="reply-a")
    copy = ChatMessageAssistant(content=resent, id="reply-a")
    assigner = TraceMessageIds(source_ids=True)

    assigner.apply_messages([reply], "call-1")
    assigner.apply_messages([copy], "call-2")

    assert (copy.id == "reply-a") is same_message
