"""Event-stubbing primitives for the two-pass streaming events skeleton.

Design context: see
``docs/superpowers/specs/2026-07-03-streaming-events-scanning-design.md``
(pass 1 of the two-pass skeleton).

The streaming events path builds a "skeleton" event list by streaming a
``TranscriptHandle`` once and replacing bulk-content events with stripped
stand-ins ("stubs"). The unmodified ``timeline_build`` classifier then runs
on the skeleton exactly as it would on the materialized transcript, to
determine span structure and which spans/regions are scannable. A second
pass later re-streams the handle and substitutes back the *full* events
that pass 1 determined are actually needed (see
``inspect_ai.event._timeline.timeline_build`` for the classifier itself).

For this to work, stubs must preserve every signal the classifier reads:

- ``uuid`` / ``span_id`` / timestamps: identity and positioning.
- For ``ModelEvent``: the system prompt (read by
  ``_get_system_prompt_for_event``, ``_timeline.py:1124``) and whether the
  event has tool calls (read by ``_has_tool_calls``, ``_timeline.py:1143``).
  ``_is_single_turn`` (``_timeline.py:1280``) counts direct ModelEvents and
  ToolEvents per span, which is why stubbing never collapses or drops
  events -- one stub per original event, always.
- For ``ToolEvent``: ``agent`` / ``agent_span_id`` / ``function`` (read by
  ``_is_agent_span`` and ``_extract_agent_results``, ``_timeline.py:1038``).

Known, accepted fidelity loss: ``_extract_agent_results``' bridge flow
(``_timeline.py:1072-1090``) reads the *next* ModelEvent's ``input`` for a
``ChatMessageTool`` whose ``tool_call_id`` matches the agent span. Our
``ModelEvent`` stub reduces ``input`` to system messages only, so that
lookup will not find a match against a stubbed ModelEvent. This only
affects ``TimelineSpan.agent_result``, which is populated for UI display
and is not read by ``_walk_spans`` (``_transcript/timeline.py``) or
``span_messages`` (``_transcript/messages.py``) -- the two functions the
scanning path depends on. So this loss is display-only and acceptable for
the scanning skeleton.
"""

from __future__ import annotations

import dataclasses

from inspect_ai.event import Event, ModelEvent, ToolEvent
from inspect_ai.model import ChatMessageSystem, ContentText


class _StubSkeletonUnsupported(Exception):
    """Raised when the transcript cannot be faithfully represented by a stub skeleton.

    Reserved for the uuid-less event fallback path (events lacking a
    ``uuid`` cannot be targeted for full-event substitution in pass 2).
    """


class _PromptInterner:
    """Dict-backed interner for system-prompt strings.

    Agentic transcripts commonly repeat the same system prompt across
    hundreds or thousands of ``ModelEvent``s. Interning ensures the stub
    skeleton retains only one copy of each distinct prompt string instead
    of one copy per event.
    """

    def __init__(self) -> None:
        self._pool: dict[str, str] = {}

    def intern(self, s: str) -> str:
        """Return a canonical instance for `s`, storing it on first sight.

        Args:
            s: The string to intern.

        Returns:
            `s` itself the first time a given value is seen; on subsequent
            calls with an equal string, the exact same instance stored
            from the first call.
        """
        existing = self._pool.get(s)
        if existing is not None:
            return existing
        self._pool[s] = s
        return s


def _stub_model_event(event: ModelEvent, interner: _PromptInterner) -> ModelEvent:
    """Return a stripped copy of `event` preserving classification signals.

    Keeps `uuid`, `span_id`, timestamps, `input` reduced to only its
    `ChatMessageSystem` entries (string content interned; list content has
    each `ContentText` part's text interned in place), and `output`
    reduced to preserve `_has_tool_calls` (first choice's message with
    `tool_calls` kept -- but with each call's `arguments` emptied, since
    `_has_tool_calls` only checks truthiness of the list -- content
    emptied; other choices dropped).

    Args:
        event: The `ModelEvent` to stub.
        interner: Interner used to dedupe system-prompt content strings.

    Returns:
        A `model_copy` of `event` with bulk content removed.
    """
    system_messages: list[ChatMessageSystem] = []
    for msg in event.input:
        if isinstance(msg, ChatMessageSystem):
            if isinstance(msg.content, str):
                system_messages.append(
                    msg.model_copy(update={"content": interner.intern(msg.content)})
                )
            else:
                # `_get_system_prompt_for_event` reads each part's `.text`
                # (only `ContentText` parts have one; other content types,
                # e.g. images, are already small relative to bulk
                # conversation content and are kept as-is). Intern each
                # `ContentText` part's text so repeated list-content
                # system prompts are deduped the same way string-content
                # ones are.
                interned_content = [
                    part.model_copy(update={"text": interner.intern(part.text)})
                    if isinstance(part, ContentText)
                    else part
                    for part in msg.content
                ]
                system_messages.append(
                    msg.model_copy(update={"content": interned_content})
                )

    if event.output.choices:
        first_choice = event.output.choices[0]
        stub_tool_calls = (
            [
                dataclasses.replace(call, arguments={})
                for call in first_choice.message.tool_calls
            ]
            if first_choice.message.tool_calls
            else first_choice.message.tool_calls
        )
        stub_message = first_choice.message.model_copy(
            update={"content": "", "tool_calls": stub_tool_calls}
        )
        stub_choices = [first_choice.model_copy(update={"message": stub_message})]
    else:
        stub_choices = []
    stub_output = event.output.model_copy(
        update={"choices": stub_choices, "completion": ""}
    )

    return event.model_copy(
        update={
            "input": system_messages,
            "input_refs": None,
            "tools": [],
            "call": None,
            "output": stub_output,
        }
    )


def _stub_tool_event(event: ToolEvent, interner: _PromptInterner) -> ToolEvent:
    """Return a stripped copy of `event` preserving classification signals.

    Keeps everything except `arguments`, `result`, and `view`, which carry
    the bulk tool-call payload. `agent`, `agent_span_id`, `function`, and
    `id` -- read by `_is_agent_span` / `_extract_agent_results` -- are
    preserved unchanged.

    `events` is NOT emptied: `inspect_ai`'s `_event_to_node` treats a
    `ToolEvent` with both `.agent` set and non-empty `.events` as a
    tool-spawned agent, recursively expanding `.events` into a nested
    `TimelineSpan` (see `_timeline.py`'s `_event_to_node`). Emptying it
    would collapse that nested span, hiding its `ModelEvent`s from pass-1
    selection. Instead, each nested event is recursively stubbed via
    `stub_event`, which still strips bulk content (nested `ModelEvent`s
    lose their bulk input/output, nested `ToolEvent`s are stripped the
    same way, recursively) while preserving the uuids and structure the
    classifier and pass-2 substitution need.

    Args:
        event: The `ToolEvent` to stub.
        interner: Interner used to dedupe nested `ModelEvent` system-prompt
            content strings across the transcript.

    Returns:
        A `model_copy` of `event` with bulk content removed.
    """
    return event.model_copy(
        update={
            "arguments": {},
            "result": "",
            "events": [stub_event(e, interner) for e in event.events],
            "view": None,
        }
    )


def stub_event(event: Event, interner: _PromptInterner) -> Event:
    """Return a bulk-content-stripped stand-in for `event`.

    `ModelEvent` and `ToolEvent` are reduced to the fields the
    `inspect_ai.event._timeline` classifier reads (see module docstring).
    Every other event type is returned unchanged: they are either already
    small (`CompactionEvent`, `SpanBeginEvent`, `SpanEndEvent`,
    `BranchEvent`, `AnchorEvent`) or are positional-only w.r.t.
    classification and kept-by-default per the stubbing spec.

    Args:
        event: The event to stub.
        interner: Interner used to dedupe `ModelEvent` system-prompt
            content strings across the transcript.

    Returns:
        The (possibly stripped) event. Always preserves `uuid` and
        `span_id` so pass 2 can substitute full events back in by uuid.
    """
    if isinstance(event, ModelEvent):
        return _stub_model_event(event, interner)
    if isinstance(event, ToolEvent):
        return _stub_tool_event(event, interner)
    return event
