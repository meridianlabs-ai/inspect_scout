"""OpenClaw telemetry-hal event + message conversion.

Builds the Inspect AI event stream and the main-thread ``ChatMessage`` list from
the consolidated intermediate produced by :mod:`.parse`.

Mapping (mirrors the Claude Code importer):

- The orchestrator (any orchestrator-surface session — ``main``, ``telegram``,
  ``dashboard``, ``cron``, ``explicit``) is the spine: its turns become the
  root-level ``ModelEvent`` / ``ToolEvent`` / ``CompactionEvent`` stream and the
  main ``messages`` thread.
- Each delegated sub-agent becomes a nested **agent span**
  (``SpanBeginEvent`` / ``SpanEndEvent``, ``type="agent"``) anchored at the
  ``sessions_spawn`` tool call that created it — or, when no spawn call is
  linkable (e.g. cron/system-spawned sessions), placed at its file-order
  anchor. Sub-agent messages are excluded from the main thread.
- Inbound operator messages (``message.in``) mark the matching user turns
  ``source="operator"`` (occurrence-for-occurrence, in time order); an inbound
  message with no matching user turn (it never entered the session thread)
  becomes its own operator-sourced user message in the thread — excluded from
  later ``ModelEvent.input``, which reflects only what the model was shown.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from logging import getLogger
from typing import Any, Literal, cast

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
    ChatMessageTool,
    ChatMessageUser,
    Content,
    GenerateConfig,
    ModelOutput,
    ModelUsage,
    StopReason,
)
from inspect_ai.tool import ToolCall, ToolCallContent, ToolCallError
from inspect_ai.tool import ToolResult as ToolResultContent

from .extraction import (
    content_blocks,
    content_to_text,
    rich_or_text,
    toolcalls_of,
    usage_to_inspect,
)
from .parse import OpenClawTelemetry, SubagentSpan, ToolResult

logger = getLogger(__name__)


_EPOCH = datetime.fromtimestamp(0, tz=timezone.utc)

# OpenClaw ``stopReason`` -> Inspect ``StopReason``. ``error`` (and any
# unrecognized value) maps to ``unknown`` and carries the turn's ``errorMessage``
# through to the model event (see :func:`_stop_and_error`).
_STOP_REASON: dict[str, StopReason] = {
    "stop": "stop",
    "toolUse": "tool_calls",
    "length": "max_tokens",
}


def _stop_and_error(turn: dict[str, Any]) -> tuple[StopReason, str | None]:
    """Map an OpenClaw turn's recorded ``stopReason`` to Inspect's stop reason.

    telemetry-hal records a ``stopReason`` on every assistant turn (``stop``,
    ``toolUse``, or ``error``) and an ``errorMessage`` on the errored ones.
    Deriving the stop reason from whether tool calls were parsed would silently
    turn length/error turns into normal completions and discard the error, so
    the recorded reason is mapped instead. An unrecognized or errored reason
    becomes ``unknown`` and propagates ``errorMessage``. A missing reason
    (non-conformant input) falls back to ``stop``.
    """
    raw = turn.get("stopReason")
    if raw in _STOP_REASON:
        return _STOP_REASON[raw], None
    if raw is None:
        return "stop", None
    message = turn.get("errorMessage")
    return "unknown", (str(message) if message else None)


def _match_text(content: object) -> str:
    """A message ``content`` as comparable text for operator reconciliation.

    Both sides flatten through :func:`.extraction.content_to_text`: an inbound
    ``message.in`` is a plain string, but its user turn may have re-entered
    the thread as a content-block list, and the two must compare equal (same
    joiner, same block filter) or the turn is left unstamped and the send
    duplicated as a standalone message.
    """
    return content_to_text(content).strip()


def build_content(
    parse: OpenClawTelemetry,
) -> tuple[list[Event], list[ChatMessage]]:
    """Build the event stream and the main-thread messages in one pass.

    User turns, orchestrator assistant turns, and real compactions are
    interleaved by timestamp. A running conversation is threaded through both
    outputs: each ``ModelEvent.input`` carries the conversation up to that
    turn (so the events view shows user prompts and tool results, matching the
    Claude Code importer), and the full running list is the message thread.

    Inbound operator messages (``message.in``) are reconciled with the user
    turns by content, occurrence-for-occurrence in time order: each send
    stamps the first unconsumed user turn carrying the same text at-or-after
    it ``source="operator"`` (never a duplicate message). Two edge rules:
    empty text never joins (a media-only send surfaces standalone rather than
    stamping an image-only turn), and a turn with no timestamp stays eligible
    as a fallback when no at-or-after turn exists. A send with no matching
    turn — it never entered the session thread — is added as its own
    operator-sourced user message so mid-run operator interventions are
    preserved; it appears in the message thread only, NOT in later
    ``ModelEvent.input``, because the model never saw it.

    Each sub-agent agent span is inserted immediately after the orchestrator
    tool event that spawned it. A sub-agent whose spawn could not be linked to
    a tool call — cron/system-spawned sessions have no ``sessions_spawn`` call
    at all, and are the majority on scheduled runs — is placed at its
    file-order anchor (the latest orchestrator turn before the session's first
    activity) with NO spawn tool call fabricated, so its delegated activity is
    kept rather than silently lost. Sub-agent messages are excluded from the
    thread.
    """
    # Each spawned sub-agent links to the single orchestrator toolCall that
    # spawned it: a spawn result names exactly one ``childSessionKey``, so the
    # mapping is 1:1. A sub-agent with no linkable spawn call is placed by its
    # file-order anchor instead — dropping it would silently lose that
    # session's activity (46 of 101 sub-agent sessions on a real
    # cron-scheduled CRUX capture).
    subagent_by_tool_call: dict[str, SubagentSpan] = {}
    unlinked: list[SubagentSpan] = []
    for sa in parse.subagents:
        tc_id = sa.spawn_tool_call_id
        if tc_id is None:
            unlinked.append(sa)
        elif tc_id in subagent_by_tool_call:
            # A second claim on the same spawn call violates the documented
            # 1:1 spawn->session mapping (corrupt/ambiguous linkage). Place it
            # like a spawn-less session, but — unlike that normal cron
            # pattern — surface the anomaly as a warning.
            logger.warning(
                "OpenClaw sub-agent %s claims spawn call %s already claimed "
                "by %s; placing it by file-order anchor instead",
                sa.session_key,
                tc_id,
                subagent_by_tool_call[tc_id].session_key,
            )
            unlinked.append(sa)
        else:
            subagent_by_tool_call[tc_id] = sa
    unlinked.sort(key=lambda sa: sa.anchor_ts)
    if unlinked:
        logger.info(
            "Placing %d OpenClaw sub-agent(s) without a linkable spawn call "
            "by file-order anchor: %s",
            len(unlinked),
            ", ".join(sa.session_key for sa in unlinked),
        )

    # The inbound operator channel (``message.in``). Each send pairs with at
    # most ONE user turn carrying the same text — the first unconsumed one
    # at-or-after the send, since a message can only enter the session thread
    # after it arrives (observed lags on real captures run from 0 to minutes;
    # user turns carry no idempotencyKey there, so text is the only join key).
    # Set-of-texts matching would silently drop a repeated send once its first
    # occurrence matched, and could stamp a twin turn that predates the send.
    # A send with no matching turn (it never entered the session thread, e.g.
    # delivered while the agent was busy) becomes its own operator-sourced
    # user message, placed by its timestamp.
    # Empty text never joins: a content-less send (media-only) and an
    # image-only turn both flatten to "", and pairing them would stamp an
    # unrelated turn. Empty sends surface standalone. A turn with NO
    # timestamp cannot fail the at-or-after check — it stays eligible
    # (surfacing a duplicate would be worse than the loose match), but only
    # as a FALLBACK: a turn satisfying at-or-after wins first, so a ts-less
    # twin never steals a send whose true match exists.
    turns_by_text: dict[str, list[dict[str, Any]]] = {}
    for user_turn in parse.user_turns:  # already timestamp-sorted
        turn_text = _match_text(user_turn.get("content"))
        if turn_text:
            turns_by_text.setdefault(turn_text, []).append(user_turn)
    operator_turn_ids: set[int] = set()
    extra_operator: list[dict[str, Any]] = []
    for m in sorted(
        parse.operator_messages, key=lambda m: int(m.get("timestamp") or 0)
    ):
        text = _match_text(m.get("content"))
        queue = turns_by_text.get(text, []) if text else []
        m_ts = int(m.get("timestamp") or 0)
        turn: dict[str, Any] | None = next(
            (
                t
                for t in queue
                if (t_ts := int(t.get("timestamp") or 0)) != 0 and t_ts >= m_ts
            ),
            None,
        )
        if turn is None:
            turn = next((t for t in queue if int(t.get("timestamp") or 0) == 0), None)
        if turn is not None:
            queue.remove(turn)
            operator_turn_ids.add(id(turn))
        else:
            extra_operator.append(m)

    # Merge user turns + operator messages + assistant turns + real compactions,
    # ordered by timestamp.
    ordered: list[tuple[int, str, dict[str, Any]]] = (
        [(int(t.get("timestamp") or 0), "user", t) for t in parse.user_turns]
        + [(int(m.get("timestamp") or 0), "operator", m) for m in extra_operator]
        + [
            (int(t.get("timestamp") or 0), "assistant", t)
            for t in parse.orchestrator_turns
        ]
        + [(int(c.get("timestamp") or 0), "compaction", c) for c in parse.compactions]
    )
    ordered.sort(key=lambda item: item[0])

    events: list[Event] = []
    thread: list[ChatMessage] = []  # the final message thread (all messages)
    conversation: list[ChatMessage] = []  # what the model saw (ModelEvent.input)
    order = 0  # monotonic working_start ordinal (stable tie-break for the timeline)
    last_ts = _ts_to_datetime(ordered[0][0]) if ordered else None
    last_ts = last_ts or _EPOCH

    for ts_ms, kind, item in ordered:
        ts = _ts_to_datetime(ts_ms) or last_ts
        last_ts = ts

        # Emit any unlinked sub-agent spans whose file-order anchor has been
        # passed, so each lands immediately AFTER the orchestrator turn the
        # run was on when the session first appeared. Strictly-before (<): a
        # span whose anchor EQUALS this item's ts belongs on the far side of
        # the anchor turn — the turn had already been produced when the
        # session appeared. Running the flush on every timeline item keeps
        # the span as close to its anchor as possible (in particular, before
        # an interleaved compaction rather than after it); the trailing loop
        # below covers anchors at or past the last item. Each span is STAMPED
        # at its own anchor time — not this (later) item's — falling back to
        # the current ts only for a zero/invalid anchor.
        while unlinked and unlinked[0].anchor_ts < ts_ms:
            anchored = unlinked.pop(0)
            order = _emit_subagent_span(
                events,
                anchored,
                _ts_to_datetime(anchored.anchor_ts) or ts,
                order,
                parse.result_by_callid,
                spawn_tool=None,
            )

        if kind == "user":
            # An operator-delivered turn carries its true source; other user
            # turns (runtime context, inter-session messages) carry none.
            source: Literal["operator"] | None = (
                "operator" if id(item) in operator_turn_ids else None
            )
            user_msg = ChatMessageUser(
                content=rich_or_text(item.get("content")), source=source
            )
            thread.append(user_msg)
            conversation.append(user_msg)
            continue

        if kind == "operator":  # message.in not present in the session thread
            # Thread-only: the model never saw this message, so it must not
            # appear in later ModelEvents' input.
            thread.append(
                ChatMessageUser(
                    content=rich_or_text(item.get("content")), source="operator"
                )
            )
            continue

        if kind == "compaction":
            # ``tokensBefore`` is recorded per compactionSummary; ``tokensAfter``
            # is not in the export. Leave unknown fields as None (the convention
            # in the other importers) rather than asserting a fabricated 0.
            tokens_before = item.get("tokensBefore")
            events.append(
                CompactionEvent(
                    source="openclaw",
                    tokens_before=int(tokens_before)
                    if tokens_before is not None
                    else None,
                    timestamp=ts,
                    working_start=float(order),
                )
            )
            order += 1
            continue

        # Assistant turn: emit a model event (carrying the conversation so far as
        # input), then its tool events.
        toolcalls = toolcalls_of(item.get("content"))
        tool_calls = [_to_tool_call(tc) for tc in toolcalls]
        turn_model = str(item["model"])
        assistant_msg = ChatMessageAssistant(
            content=content_blocks(item.get("content")),
            tool_calls=tool_calls or None,
            model=turn_model,
        )
        usage = ModelUsage(**usage_to_inspect(item.get("usage") or {}))
        stop_reason, turn_error = _stop_and_error(item)
        output = ModelOutput(
            model=turn_model,
            choices=[
                ChatCompletionChoice(
                    message=assistant_msg,
                    stop_reason=stop_reason,
                )
            ],
            usage=usage,
            error=turn_error,
        )
        # PERF (O(n²), ~147s on the 1.14GB CRUX1 file): passing the growing
        # conversation snapshot to the ModelEvent constructor re-validates every
        # message each turn.
        events.append(
            ModelEvent(
                model=turn_model,
                input=list(conversation),  # what the model saw before this turn
                tools=[],
                tool_choice="auto",
                config=GenerateConfig(),
                output=output,
                error=turn_error,
                timestamp=ts,
                completed=ts,
                working_start=float(order),
            )
        )
        order += 1
        thread.append(assistant_msg)
        conversation.append(assistant_msg)

        for tc in toolcalls:
            tc_id = str(tc.get("id") or "")
            function = str(tc.get("name") or "unknown")
            arguments = tc.get("arguments") or {}
            result_content, completed, error, failed = _tool_result_fields(
                parse.result_by_callid.get(tc_id), ts
            )
            linked = subagent_by_tool_call.get(tc_id)

            if linked is not None:
                # A spawn that delegated to a sub-agent. Mirror the Claude Code
                # importer: fold the spawn tool INTO the agent span (as its
                # first child, tagged with ``agent_span_id``) rather than
                # emitting a standalone root-level tool event.
                order = _emit_subagent_span(
                    events, linked, ts, order, parse.result_by_callid, spawn_tool=tc
                )
            else:
                events.append(
                    ToolEvent(
                        id=tc_id,
                        function=function,
                        arguments=arguments if isinstance(arguments, dict) else {},
                        result=cast(ToolResultContent, result_content),
                        error=error,
                        failed=failed,
                        timestamp=ts,
                        completed=completed,
                        working_start=float(order),
                    )
                )
                order += 1

            # The tool result still belongs in the orchestrator message thread,
            # whether or not the tool spawned a sub-agent.
            tool_msg = ChatMessageTool(
                content=result_content,
                tool_call_id=tc_id,
                function=function,
                error=error,
            )
            thread.append(tool_msg)
            conversation.append(tool_msg)

    # Any unlinked sub-agent spans anchored after the last orchestrator turn.
    for sa in unlinked:
        order = _emit_subagent_span(
            events,
            sa,
            _ts_to_datetime(sa.anchor_ts) or last_ts,
            order,
            parse.result_by_callid,
            spawn_tool=None,
        )

    return events, thread


def _emit_subagent_span(
    events: list[Event],
    sa: SubagentSpan,
    timestamp: datetime,
    order: int,
    result_by_callid: dict[str, ToolResult],
    spawn_tool: dict[str, Any] | None,
) -> int:
    """Emit a delegated sub-agent as a nested agent span and return next order.

    The span (``type="agent"``) wraps the sub-agent's reconstructed activity,
    linked to the span via ``span_id`` so ``event_tree`` nests it. Mirroring the
    Claude Code importer, the orchestrator ``sessions_spawn`` call
    (``spawn_tool``) is emitted as the span's FIRST child, tagged with
    ``agent_span_id`` so the view folds it into the agent header rather than
    drawing a standalone tool row. ``spawn_tool`` is ``None`` for an unlinked
    (anchor-placed) session — no spawn call was recorded, so none is emitted
    (fabricating one would forge telemetry that does not exist).

    - Schema A: each ``messages[]`` assistant turn becomes a ``ModelEvent``
    (with usage) followed by its ``ToolEvent``s (results matched by
    ``toolCallId``), threading a sub-agent-local conversation as input. - Schema
    B: each ``tool.*`` call becomes a ``ToolEvent`` (raw tool name + params; no
    result body or usage is recorded in this schema). A schema-B span therefore
    has no model turns, token totals, or wall-clock duration (it renders ``0 ·
    0s``), and the sub-agent's final response is NOT shown: it is only present
    as an unattributable ``message.out`` event (see :mod:`.parse` and this
    example's ``README.md``).

    Some exports are *hybrid*: the same calls appear both as ``messages[]``
    ``toolCall`` blocks AND as ``tool.*`` events. The schema-A turns are
    authoritative (they carry results), so the ``tool.*`` events are only
    reconstructed when no schema-A turns are present, to avoid emitting each
    tool call twice.
    """
    span_id = sa.session_key
    span_end_ts = timestamp
    events.append(
        SpanBeginEvent(
            id=span_id,
            name=(
                sa.spawn_label
                or _short_description(_task_line(sa.prompt))
                or "subagent"
            ),
            type="agent",
            timestamp=timestamp,
            working_start=float(order),
            metadata={
                "session_key": sa.session_key,
                "description": _short_description(sa.spawn_task),
                "task": sa.spawn_task,
                "prompt": sa.prompt,
                "n_tool_calls": sa.n_tool_calls,
                "n_assistant_turns": sa.n_assistant_turns,
            },
        )
    )
    order += 1

    # The spawning sessions_spawn call, folded into the agent span (mirrors the
    # Claude Code importer's Task-tool handling) so it is not shown as a
    # separate root-level tool event. An unlinked (anchor-placed) session has
    # no spawn call to fold in.
    if spawn_tool is not None:
        spawn_id = str(spawn_tool.get("id") or "")
        spawn_function = str(spawn_tool.get("name") or "sessions_spawn")
        spawn_arguments = spawn_tool.get("arguments") or {}
        spawn_arguments = spawn_arguments if isinstance(spawn_arguments, dict) else {}
        spawn_result, spawn_completed, spawn_error, spawn_failed = _tool_result_fields(
            result_by_callid.get(spawn_id), timestamp
        )
        span_end_ts = max(span_end_ts, spawn_completed)
        events.append(
            ToolEvent(
                id=spawn_id,
                function=spawn_function,
                arguments=spawn_arguments,
                result=cast(ToolResultContent, spawn_result),
                error=spawn_error,
                failed=spawn_failed,
                timestamp=timestamp,
                completed=spawn_completed,
                working_start=float(order),
                span_id=span_id,
                agent_span_id=span_id,
                view=_tool_call_view(spawn_function, spawn_arguments),
            )
        )
        order += 1

    # Schema A: rebuild the sub-agent's own model + tool events from its turns.
    sub_messages: list[ChatMessage] = []
    if sa.prompt:
        sub_messages.append(ChatMessageUser(content=sa.prompt))
    for turn in sa.turns:
        toolcalls = toolcalls_of(turn.get("content"))
        tool_calls = [_to_tool_call(tc) for tc in toolcalls]
        turn_model = str(turn["model"])
        assistant_msg = ChatMessageAssistant(
            content=content_blocks(turn.get("content")),
            tool_calls=tool_calls or None,
            model=turn_model,
        )
        stop_reason, turn_error = _stop_and_error(turn)
        output = ModelOutput(
            model=turn_model,
            choices=[
                ChatCompletionChoice(
                    message=assistant_msg,
                    stop_reason=stop_reason,
                )
            ],
            usage=ModelUsage(**usage_to_inspect(turn.get("usage") or {})),
            error=turn_error,
        )
        turn_ts = _ts_to_datetime(turn.get("timestamp")) or timestamp
        span_end_ts = max(span_end_ts, turn_ts)
        events.append(
            ModelEvent(
                model=turn_model,
                input=list(sub_messages),
                tools=[],
                tool_choice="auto",
                config=GenerateConfig(),
                output=output,
                error=turn_error,
                timestamp=turn_ts,
                completed=turn_ts,
                working_start=float(order),
                span_id=span_id,
            )
        )
        order += 1
        sub_messages.append(assistant_msg)

        for tc in toolcalls:
            tc_id = str(tc.get("id") or "")
            function = str(tc.get("name") or "unknown")
            arguments = tc.get("arguments") or {}
            result_content, completed, error, failed = _tool_result_fields(
                result_by_callid.get(tc_id), turn_ts
            )
            span_end_ts = max(span_end_ts, completed)
            events.append(
                ToolEvent(
                    id=tc_id,
                    function=function,
                    arguments=arguments if isinstance(arguments, dict) else {},
                    result=cast(ToolResultContent, result_content),
                    error=error,
                    failed=failed,
                    timestamp=turn_ts,
                    completed=completed,
                    working_start=float(order),
                    span_id=span_id,
                )
            )
            order += 1
            sub_messages.append(
                ChatMessageTool(
                    content=result_content,
                    tool_call_id=tc_id,
                    function=function,
                    error=error,
                )
            )

    # Schema B: rebuild tool calls from tool.* events (no result body / usage).
    # Skipped when schema-A turns exist (hybrid exports duplicate the calls).
    for idx, call in enumerate(sa.tool_calls if not sa.turns else []):
        params = call.get("params")
        metadata = {
            key: value
            for key, value in (
                ("duration_ms", call.get("durationMs")),
                ("success", call.get("success")),
            )
            if value is not None
        }
        # Prefer the tool.*'s own ``ts`` (enriched envelope) so a call carries a
        # real start->end span; fall back to the spawn time when absent (bare
        # captures), which never mis-orders it. Bare captures record no
        # ``endTs`` either, but ``durationMs`` (from tool.end) still gives the
        # call a real width — downstream busy-time sums rely on it — so only a
        # call with neither collapses to zero duration.
        call_start = _ts_to_datetime(call.get("startTs")) or timestamp
        duration_ms = _duration_to_ms(call.get("durationMs"))
        call_end = _ts_to_datetime(call.get("endTs")) or (
            call_start + timedelta(milliseconds=duration_ms)
            if duration_ms
            else call_start
        )
        # A recorded ``success`` of false is a real failure: surface it through
        # the standard ToolEvent fields (with the tool.end ``error`` as the
        # message) rather than leaving ``failed``/``error`` unset.
        success = call.get("success")
        failed = None if success is None else not success
        err_text = call.get("error")
        error = ToolCallError("unknown", str(err_text)) if err_text else None
        events.append(
            ToolEvent(
                id=f"{span_id}:tool:{idx}",
                function=str(call.get("toolName") or "unknown"),
                arguments=params if isinstance(params, dict) else {},
                result="",
                error=error,
                failed=failed,
                timestamp=call_start,
                completed=call_end,
                working_start=float(order),
                span_id=span_id,
                metadata=metadata or None,
            )
        )
        span_end_ts = max(span_end_ts, call_end)
        order += 1

    events.append(
        SpanEndEvent(
            id=span_id,
            timestamp=span_end_ts,
            working_start=float(order),
        )
    )
    order += 1
    return order


def _tool_result_fields(
    result: ToolResult | None,
    started: datetime,
) -> tuple[str | list[Content], datetime, ToolCallError | None, bool | None]:
    """Resolve a ``ToolResult`` into ``ToolEvent`` fields.

    Returns ``(content, completed, error, failed)``. ``content`` is the result
    body (a plain string, or ``Content`` blocks when it carries images). The
    completion time comes from the result's own timestamp when present (so the
    event carries a real call→result span) and otherwise falls back to
    ``started`` (the parent turn's time). ``isError`` maps to Inspect's
    ``failed`` flag and, when the call errored, a ``ToolCallError`` carrying the
    result text — the authoritative, id-keyed success/error signal (see
    :class:`ToolResult`).
    """
    if result is None:
        return "", started, None, None
    completed = _ts_to_datetime(result.timestamp) or started
    if result.is_error:
        return result.content, completed, ToolCallError("unknown", result.text), True
    # is_error False -> known-success; None -> unknown (leave ``failed`` unset).
    failed = False if result.is_error is False else None
    return result.content, completed, None, failed


def _ts_to_datetime(value: Any) -> datetime | None:
    """Convert an OpenClaw epoch-millisecond timestamp to a UTC ``datetime``."""
    if value is None:
        return None
    try:
        ms = int(value)
    except (TypeError, ValueError):
        return None
    if ms <= 0:
        return None
    return datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc)


def _duration_to_ms(value: Any) -> int | None:
    """Coerce a telemetry ``durationMs`` to positive-int milliseconds.

    The value comes verbatim out of ``json.loads``, so guard it the way
    ``_ts_to_datetime`` guards timestamps: a numeric string still yields a
    width; a non-numeric or non-positive value yields ``None`` (zero width)
    rather than aborting the import inside ``timedelta`` arithmetic — or
    placing a call's completion before its start.
    """
    try:
        ms = int(value)
    except (TypeError, ValueError):
        return None
    return ms if ms > 0 else None


_TASK_TAG = "[Subagent Task]"


def _is_task_bearing(line: str) -> bool:
    """A prompt line usable as a span name.

    Non-empty, not a bracketed line (scaffold tags, timestamps, and template
    placeholders all take that shape — an unrecognized bracket line must
    never become a name), and not the subagent boilerplate sentence.
    """
    return (
        bool(line)
        and not line.startswith("[")
        and "you are running as a subagent" not in line.lower()
    )


def _task_line(prompt: str | None) -> str | None:
    """The first task-bearing line of a sub-agent prompt, for span naming.

    A spawn-less (anchor-placed) session has no ``label``/``task`` arguments to
    name its span from, only its own prompt — which opens with OpenClaw's
    scaffold preamble (a timestamp tag and/or ``[Subagent Context] You are
    running as a subagent…``) and usually announces the task with a
    ``[Subagent Task]`` tag: inline (``[Subagent Task]: <task>``), possibly
    sharing its line with the timestamp preamble, or with the task on a
    following line. The tag is authoritative when present anywhere on a line,
    and prompts may repeat it — a bare heading first, the task-carrying tag
    line after — so a bare tag's lookahead runs only up to the NEXT tag line
    and defers to it, applying the same bracket/boilerplate skip as the
    no-tag fallback. Returns ``None`` when nothing task-bearing is found.
    """
    lines = [line.strip() for line in (prompt or "").splitlines()]
    tag_idxs = [i for i, line in enumerate(lines) if _TASK_TAG in line]
    for pos, i in enumerate(tag_idxs):
        line = lines[i]
        inline = line[line.find(_TASK_TAG) + len(_TASK_TAG) :].lstrip(" :").strip()
        if inline:
            return inline
        stop = tag_idxs[pos + 1] if pos + 1 < len(tag_idxs) else len(lines)
        for follow in lines[i + 1 : stop]:
            if _is_task_bearing(follow):
                return follow
    if tag_idxs:
        return None
    for line in lines:
        if _is_task_bearing(line):
            return line
    return None


def _short_description(task: str | None, limit: int = 80) -> str | None:
    """First line of a spawn ``task``, trimmed for use as a span description."""
    if not task:
        return None
    first = task.strip().splitlines()[0].strip() if task.strip() else ""
    if len(first) > limit:
        first = first[: limit - 1].rstrip() + "…"
    return first or None


def _tool_call_view(function: str, arguments: dict[str, Any]) -> ToolCallContent | None:
    """Custom rendering for known OpenClaw tools (mirrors Claude Code's views).

    A ``sessions_spawn`` is rendered as an ``Agent: <label>`` block with the
    delegated ``task`` as the body — the ``{{task}}`` placeholder is filled from
    the call's arguments by the viewer, exactly as Claude Code's Task/Agent view
    fills ``{{description}}``/``{{prompt}}``. Other tools have no custom view.
    """
    if function != "sessions_spawn":
        return None
    label = str(arguments.get("label") or "")
    return ToolCallContent(
        title=f"Agent: {label}" if label else "Agent",
        format="markdown",
        content="{{task}}",
    )


def _to_tool_call(tc: dict[str, Any]) -> ToolCall:
    """Build an Inspect ``ToolCall`` from a raw OpenClaw ``toolCall`` block.

    Carries a custom ``view`` for tools that have one (see
    :func:`_tool_call_view`) so the model-call rendering matches Claude Code's.
    """
    function = str(tc.get("name") or "unknown")
    arguments = tc.get("arguments") or {}
    arguments = arguments if isinstance(arguments, dict) else {}
    return ToolCall(
        id=str(tc.get("id") or ""),
        function=function,
        arguments=arguments,
        view=_tool_call_view(function, arguments),
    )
