"""Tests for the stable_message_ids replacement (inspect_scout._util).

This is a drop-in replacement for ``inspect_ai.model.stable_message_ids`` with a
performance fix; these tests pin the observable contract the fix must preserve.

TODO: Delete this module once https://github.com/UKGovernmentBEIS/inspect_ai/pull/4407
merged.
"""

from __future__ import annotations

from inspect_ai.event import ModelEvent
from inspect_ai.model import (
    ChatCompletionChoice,
    ChatMessage,
    ChatMessageAssistant,
    ChatMessageUser,
    GenerateConfig,
    ModelOutput,
)
from inspect_scout._util._message_ids import stable_message_ids


def _model_event(inputs: list[ChatMessage]) -> ModelEvent:
    return ModelEvent(
        model="m",
        input=list(inputs),
        tools=[],
        tool_choice="auto",
        config=GenerateConfig(),
        output=ModelOutput.from_content("m", "out"),
    )


def test_all_messages_receive_ids() -> None:
    msgs: list[ChatMessage] = [
        ChatMessageUser(content="hi"),
        ChatMessageAssistant(content="yo"),
    ]
    stable_message_ids()(msgs)
    assert all(m.id for m in msgs)


def test_identical_content_same_id_across_events() -> None:
    # The whole point of "stable": a message that recurs in a later call's input
    # (distinct object, identical content) gets the SAME id -> cross-event
    # identity. This is the case the importer relies on (growing inputs).
    shared = "what is the weather?"
    e1 = _model_event([ChatMessageUser(content=shared)])
    e2 = _model_event(
        [ChatMessageUser(content=shared), ChatMessageAssistant(content="sunny")]
    )
    apply = stable_message_ids()
    apply(e1)
    apply(e2)
    assert e1.input[0].id == e2.input[0].id


def test_duplicate_content_within_conversation_gets_distinct_ids() -> None:
    # Two identical-content messages in the SAME conversation must not collapse
    # to one id (otherwise they'd be indistinguishable within that turn).
    dup = ChatMessageUser(content="same")
    dup2 = ChatMessageUser(content="same")
    stable_message_ids()([dup, dup2])
    assert dup.id and dup2.id and dup.id != dup2.id


def test_distinct_content_gets_distinct_ids() -> None:
    a = ChatMessageUser(content="alpha")
    b = ChatMessageUser(content="beta")
    stable_message_ids()([a, b])
    assert a.id != b.id


def test_model_event_output_message_gets_id() -> None:
    e = _model_event([ChatMessageUser(content="hi")])
    stable_message_ids()(e)
    assert isinstance(e.output, ModelOutput)
    assert e.output.message.id


def test_output_id_distinct_from_identical_input_content() -> None:
    # An output message whose content matches an input message must still get a
    # fresh id within that conversation (same within-conversation rule).
    same = "echo"
    e = ModelEvent(
        model="m",
        input=[ChatMessageUser(content=same)],
        tools=[],
        tool_choice="auto",
        config=GenerateConfig(),
        output=ModelOutput(
            model="m",
            choices=[ChatCompletionChoice(message=ChatMessageAssistant(content=same))],
        ),
    )
    stable_message_ids()(e)
    assert isinstance(e.output, ModelOutput)
    assert e.output.message.id != e.input[0].id
