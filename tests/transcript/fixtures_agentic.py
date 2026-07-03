"""Synthetic multi-agent event fixture for streaming-events-scanning tests.

Builds a deterministic flat `Event` list (using real inspect_ai event
constructors) that exercises every classification path `timeline_build`
implements: explicit agent spans, unrolled primitive-solver spans,
tool-spawned agents, utility-agent detection (both the single-turn/
different-prompt heuristic and the foreign-prompt-helper wrapping), and
compaction events.

See `inspect_ai.event._timeline.timeline_build` for the classifier this
fixture is designed against.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Literal

from inspect_ai.event import (
    CompactionEvent,
    Event,
    ModelEvent,
    SpanBeginEvent,
    SpanEndEvent,
    ToolEvent,
)
from inspect_ai.model import (
    ChatCompletionChoice,
    ChatMessage,
    ChatMessageAssistant,
    ChatMessageSystem,
    ChatMessageUser,
    GenerateConfig,
    ModelOutput,
)
from inspect_ai.tool import ToolCall
from inspect_scout._transcript.types import Transcript

_T0 = datetime(2025, 1, 1, 0, 0, 0)

# Monotonically increasing counter so every event/timestamp/uuid is distinct
# and deterministic across calls.
_counter = 0


def _next_ts() -> datetime:
    global _counter
    _counter += 1
    return _T0 + timedelta(seconds=_counter)


def _uuid(label: str) -> str:
    return f"evt-{label}"


def _model_event(
    *,
    label: str,
    system_prompt: str,
    output_text: str,
    tool_call: ToolCall | None = None,
    span_id: str | None,
    input_messages: list[ChatMessage] | None = None,
) -> ModelEvent:
    """Build a ModelEvent with a distinct uuid and final assistant text.

    Args:
        label: Unique label used to derive the event's uuid.
        system_prompt: System prompt text placed in the input messages.
        output_text: Assistant output text (kept distinct per event so
            segment equivalence can detect selection mistakes).
        tool_call: If given, attached as a tool call on the assistant
            message's output (drives `_has_tool_calls`).
        span_id: Span the event belongs to (None for root-level).
        input_messages: If given, used verbatim as the event's ``input``
            instead of the default ``[System(system_prompt), User(...)]``.
            Used to construct precise trim-compaction overlaps (see the
            ``pre-trim``/``post-trim`` events). Any supplied list must
            still contain a ``ChatMessageSystem`` so ``timeline_build``'s
            ``_get_system_prompt_for_event`` classification is unchanged.

    Returns:
        A fully constructed ModelEvent.
    """
    ts = _next_ts()
    message = ChatMessageAssistant(
        content=output_text,
        tool_calls=[tool_call] if tool_call is not None else None,
    )
    return ModelEvent(
        span_id=span_id,
        timestamp=ts,
        completed=ts,
        uuid=_uuid(label),
        model="mockllm/model",
        input=input_messages
        if input_messages is not None
        else [
            ChatMessageSystem(content=system_prompt),
            ChatMessageUser(content=f"user-input-{label}"),
        ],
        tools=[],
        tool_choice="auto",
        config=GenerateConfig(),
        output=ModelOutput(
            model="mockllm/model",
            choices=[
                ChatCompletionChoice(message=message, stop_reason="stop"),
            ],
        ),
    )


def _tool_event(
    *,
    label: str,
    function: str,
    payload: str,
    span_id: str | None,
    agent: str | None = None,
    events: list[Event] | None = None,
) -> ToolEvent:
    """Build a ToolEvent whose arguments/result embed `payload`.

    Args:
        label: Unique label used to derive the event's uuid.
        function: Tool function name.
        payload: Payload embedded in `arguments`/`result`.
        span_id: Span the event belongs to (None for root-level).
        agent: If given, marks this as a tool-spawned agent handoff (see
            `inspect_ai.event._timeline._event_to_node`).
        events: Nested events for a tool-spawned agent (`ToolEvent.events`).
            Only meaningful together with `agent`.
    """
    ts = _next_ts()
    return ToolEvent(
        span_id=span_id,
        timestamp=ts,
        completed=ts,
        uuid=_uuid(label),
        id=f"call-{label}",
        function=function,
        arguments={"payload": payload},
        result=f"result-{payload}",
        agent=agent,
        events=events if events is not None else [],
    )


def _compaction_event(
    *, label: str, type: Literal["summary", "edit", "trim"], span_id: str | None
) -> CompactionEvent:
    ts = _next_ts()
    return CompactionEvent(
        span_id=span_id,
        timestamp=ts,
        uuid=_uuid(label),
        type=type,
    )


def _span_begin(
    *, span_id: str, name: str, span_type: str, parent_id: str | None
) -> SpanBeginEvent:
    """Build a SpanBeginEvent.

    Mirrors ``inspect_ai.util._span.span()``: the begin event's own
    ``span_id`` (the span it occurs "within") is the span's own id, since
    the current-span context is updated before the begin event is emitted.
    """
    return SpanBeginEvent(
        id=span_id,
        parent_id=parent_id,
        type=span_type,
        name=name,
        timestamp=_next_ts(),
        span_id=span_id,
    )


def _span_end(*, span_id: str) -> SpanEndEvent:
    """Build a SpanEndEvent (its ``span_id`` is the span's own id; see `_span_begin`)."""
    return SpanEndEvent(id=span_id, timestamp=_next_ts(), span_id=span_id)


def agentic_events(
    *, big_payload: str = "x" * 200, bulk_model_turns: int = 0
) -> list[Event]:
    """Build a deterministic flat event list exercising `timeline_build`.

    Structure (see module docstring and task brief for the classification
    rationale behind each piece):

    - Top-level ``solvers`` span containing:
      - ``type="agent"`` span "main":
        - 3 ModelEvents with system prompt "MAIN" (middle one has tool_calls),
          interleaved with ToolEvents carrying `big_payload`.
        - nested ``type="agent"`` span "sub": single tool-calling turn,
          system prompt "SUB" (different from parent, not tool_invoked) ->
          classified utility.
        - nested ``type="agent"`` span "sub2": 3 ModelEvents, system prompt
          "MAIN" (same as parent), multi-turn -> NOT utility, scanned.
        - ``type="solver"`` primitive span "generate" with one ModelEvent
          (prompt "MAIN") -> unrolled into main's content.
        - ``type="tool"`` span "browser" containing one ModelEvent (prompt
          "MAIN", tool_calls) -> classified as a tool-spawned agent.
        - a flat ``ToolEvent`` "handoff-tool" with ``agent="handoff_agent"``
          and 2 nested ModelEvents in ``.events`` (prompt "MAIN", multi-turn)
          -> classified as a tool-spawned agent via
          ``inspect_ai.event._timeline._event_to_node`` (distinct from the
          "browser" span-based path: no begin/end span wrapping the nested
          events).
        - one foreign-prompt helper ModelEvent (prompt "HELPER", no
          tool_calls) directly in main -> wrapped as a utility span.
        - two CompactionEvents ("summary" then "trim"), each with
          ModelEvents before/after.
        - if `bulk_model_turns` > 0, that many extra ModelEvents inserted
          directly before the final ("main-3") ModelEvent, each carrying
          `big_payload` in its (non-system) input content and a small,
          distinct output. With `compaction="last"`, only the span's final
          ModelEvent is selected, so these turns are never selected --
          their bulk lives entirely in non-selected conversations.

    Args:
        big_payload: Payload string embedded in ToolEvent arguments/results
            in the "main" span, to exercise large-content handling.
        bulk_model_turns: Number of extra bulk-carrying ModelEvents to
            insert in "main" immediately before the final ModelEvent.
            Defaults to 0 (no change to existing callers).

    Returns:
        A flat, chronologically-ordered list of `Event` objects.
    """
    global _counter
    _counter = 0

    events: list[Event] = []

    # --- solvers (top-level phase span) ---
    events.append(
        _span_begin(
            span_id="solvers", name="solvers", span_type="solvers", parent_id=None
        )
    )

    # --- main agent span ---
    events.append(
        _span_begin(span_id="main", name="main", span_type="agent", parent_id="solvers")
    )

    # ModelEvent 1 (main, no tool calls)
    events.append(
        _model_event(
            label="main-1",
            system_prompt="MAIN",
            output_text="main-output-1",
            span_id="main",
        )
    )

    # ToolEvent interleaved (carries big_payload)
    events.append(
        _tool_event(
            label="main-tool-1", function="search", payload=big_payload, span_id="main"
        )
    )

    # ModelEvent 2 (main, WITH tool calls -> sets primary prompt for
    # _wrap_utility_events)
    events.append(
        _model_event(
            label="main-2",
            system_prompt="MAIN",
            output_text="main-output-2",
            tool_call=ToolCall(
                id="call-main-2", function="search", arguments={"q": big_payload}
            ),
            span_id="main",
        )
    )

    # ToolEvent interleaved (carries big_payload in arguments)
    events.append(
        _tool_event(
            label="main-tool-2", function="search", payload=big_payload, span_id="main"
        )
    )

    # --- nested "sub" agent span: single tool-calling turn, foreign prompt,
    # not tool_invoked -> classified utility by _classify_utility_agents ---
    events.append(
        _span_begin(span_id="sub", name="sub", span_type="agent", parent_id="main")
    )
    events.append(
        _model_event(
            label="sub-1",
            system_prompt="SUB",
            output_text="sub-output-1",
            tool_call=ToolCall(id="call-sub-1", function="lookup", arguments={}),
            span_id="sub",
        )
    )
    events.append(
        _tool_event(label="sub-tool-1", function="lookup", payload="sub", span_id="sub")
    )
    events.append(
        _model_event(
            label="sub-2",
            system_prompt="SUB",
            output_text="sub-output-2",
            span_id="sub",
        )
    )
    events.append(_span_end(span_id="sub"))

    # --- nested "sub2" agent span: same prompt as parent, multi-turn (3
    # ModelEvents, no single tool-calling-turn shape) -> NOT utility ---
    events.append(
        _span_begin(span_id="sub2", name="sub2", span_type="agent", parent_id="main")
    )
    events.append(
        _model_event(
            label="sub2-1",
            system_prompt="MAIN",
            output_text="sub2-output-1",
            span_id="sub2",
        )
    )
    events.append(
        _model_event(
            label="sub2-2",
            system_prompt="MAIN",
            output_text="sub2-output-2",
            span_id="sub2",
        )
    )
    events.append(
        _model_event(
            label="sub2-3",
            system_prompt="MAIN",
            output_text="sub2-output-3",
            span_id="sub2",
        )
    )
    events.append(_span_end(span_id="sub2"))

    # --- type="solver" primitive span "generate" with one ModelEvent ->
    # gets unrolled into main's content (no nested agent span inside it) ---
    events.append(
        _span_begin(
            span_id="generate", name="generate", span_type="solver", parent_id="main"
        )
    )
    events.append(
        _model_event(
            label="generate-1",
            system_prompt="MAIN",
            output_text="generate-output-1",
            span_id="generate",
        )
    )
    events.append(_span_end(span_id="generate"))

    # --- type="tool" span "browser" containing a ModelEvent -> tool-spawned
    # agent per _is_agent_span/_build_span_from_generic_span ---
    events.append(
        _span_begin(
            span_id="browser", name="browser", span_type="tool", parent_id="main"
        )
    )
    events.append(
        _model_event(
            label="browser-1",
            system_prompt="MAIN",
            output_text="browser-output-1",
            tool_call=ToolCall(id="call-browser-1", function="click", arguments={}),
            span_id="browser",
        )
    )
    events.append(_span_end(span_id="browser"))

    # --- flat ToolEvent with `agent` set and nested `.events` -> tool-spawned
    # agent per inspect_ai's `_event_to_node` (distinct from the "browser"
    # span-based path above: no SpanBeginEvent/SpanEndEvent wrapping, the
    # nested agent's ModelEvents live inside `ToolEvent.events` itself).
    # Multi-turn, same "MAIN" prompt as parent -> scannable, not utility.
    # The second nested ModelEvent's output carries `big_payload` so
    # stripping is assertable.
    handoff_events: list[Event] = [
        _model_event(
            label="handoff-1",
            system_prompt="MAIN",
            output_text="handoff-output-1",
            tool_call=ToolCall(id="call-handoff-1", function="lookup", arguments={}),
            span_id="main",
        ),
        _model_event(
            label="handoff-2",
            system_prompt="MAIN",
            output_text=big_payload,
            span_id="main",
        ),
    ]
    events.append(
        _tool_event(
            label="handoff-tool",
            function="handoff",
            payload=big_payload,
            span_id="main",
            agent="handoff_agent",
            events=handoff_events,
        )
    )

    # --- foreign-prompt helper ModelEvent directly in main (no tool_calls)
    # -> wrapped by _wrap_utility_events as a synthetic utility span ---
    events.append(
        _model_event(
            label="helper-1",
            system_prompt="HELPER",
            output_text="helper-output-1",
            span_id="main",
        )
    )

    # --- compaction: "summary" with ModelEvents before/after ---
    events.append(
        _model_event(
            label="pre-summary",
            system_prompt="MAIN",
            output_text="pre-summary-output",
            span_id="main",
        )
    )
    events.append(
        _compaction_event(label="compaction-summary", type="summary", span_id="main")
    )
    events.append(
        _model_event(
            label="post-summary",
            system_prompt="MAIN",
            output_text="post-summary-output",
            span_id="main",
        )
    )

    # --- compaction: "trim" with ModelEvents before/after (exercises the
    # trim-first-event rule).
    #
    # A trim compaction drops a *prefix* of the conversation. For
    # `span_messages(compaction="all")` to reconstruct that dropped prefix
    # (`_trim_prefix`, messages.py), the pre-trim event's input must contain
    # leading messages that are ABSENT from the head of the post-trim event's
    # input, and the post-trim input must START with a message shared with
    # (i.e. found later in) the pre-trim input so the two can be aligned.
    #
    # Here `trim-shared` is the alignment anchor: it is the FIRST message of
    # post-trim and the THIRD message of pre-trim, so `_trim_prefix` returns
    # pre-trim's first two messages (`System("MAIN")` + `User("trim-dropped")`)
    # as the trimmed prefix. `trim-dropped` is a distinctive marker that lets
    # tests assert the prefix was actually reconstructed. Both events still
    # carry a `System("MAIN")` message so `_get_system_prompt_for_event`
    # classification is identical to their siblings.
    trim_shared = ChatMessageUser(content="trim-shared-anchor")
    events.append(
        _model_event(
            label="pre-trim",
            system_prompt="MAIN",
            output_text="pre-trim-output",
            span_id="main",
            input_messages=[
                ChatMessageSystem(content="MAIN"),
                ChatMessageUser(content="trim-dropped-marker"),
                trim_shared,
            ],
        )
    )
    events.append(
        _compaction_event(label="compaction-trim", type="trim", span_id="main")
    )
    events.append(
        _model_event(
            label="post-trim",
            system_prompt="MAIN",
            output_text="post-trim-output",
            span_id="main",
            input_messages=[
                trim_shared,
                ChatMessageSystem(content="MAIN"),
                ChatMessageUser(content="user-input-post-trim"),
            ],
        )
    )

    # Optional bulk ModelEvents, inserted directly before the closing turn.
    # With compaction="last" only the final ModelEvent in the span is
    # selected, so these are always non-selected -- their (big_payload-
    # carrying) conversations must never be retained by the stub skeleton.
    for i in range(bulk_model_turns):
        events.append(
            _model_event(
                label=f"bulk-{i}",
                system_prompt="MAIN",
                output_text=f"bulk-output-{i}",
                span_id="main",
                input_messages=[
                    ChatMessageSystem(content="MAIN"),
                    ChatMessageUser(content=f"{big_payload}-{i}"),
                ],
            )
        )

    # ModelEvent 3 (main, closing turn, no tool calls)
    events.append(
        _model_event(
            label="main-3",
            system_prompt="MAIN",
            output_text="main-output-3",
            span_id="main",
        )
    )

    events.append(_span_end(span_id="main"))
    events.append(_span_end(span_id="solvers"))

    return events


def agentic_transcript(events: list[Event] | None = None) -> Transcript:
    """Wrap `agentic_events()` (or a caller-supplied list) in a Transcript.

    Args:
        events: Event list to embed; defaults to `agentic_events()`.

    Returns:
        A minimal `Transcript` suitable for streaming/batch pipeline tests.
    """
    return Transcript.model_construct(
        transcript_id="agentic-1",
        messages=[],
        events=events if events is not None else agentic_events(),
        timelines=[],
        metadata={},
    )
