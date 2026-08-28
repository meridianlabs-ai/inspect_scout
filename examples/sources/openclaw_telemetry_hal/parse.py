"""OpenClaw telemetry-hal parsing: raw events into a consolidated intermediate.

Why an intermediate (``OpenClawTelemetry``): the raw events can't be streamed
straight into Inspect events. ``agent.*`` re-dumps a cumulative ``messages[]``
and sub-agents span two export schemas, so the consolidation (deduping recurring
turns, reconstructing sub-agent spans) is *global* work over the whole file that
must finish before any mapping starts.

The format in brief
--------------------
JSONL, one event per line. Payload-bearing events:

- ``agent.start`` / ``agent.end`` carry a ``sessionKey`` and a CUMULATIVE
  ``messages[]`` snapshot (assistant turns, ``toolResult``s,
  ``compactionSummary``s). The same turn recurs across snapshots, so turns must
  be deduped by ``responseId`` — or, when the capture carries none, by
  ``(session, timestamp, content)`` with toolCall ids masked, because
  OpenClaw's history sanitizer rewrites those ids between a turn's first
  snapshot and all later ones (see :func:`_keyless_content_json`). Snapshots may also carry scaffold
  *roll-up* records — turn-finalization aggregates whose usage restates (sums)
  the preceding per-call block; these are dropped (see
  :func:`_drop_rollup_aggregates`).
- ``tool.start`` / ``tool.end`` are individual tool calls (the only place
  schema-B sub-agent activity is recorded).
- ``sessionKey`` is ``agent:<...>:<kind>:<uuid>`` with ``kind`` one of ``main``,
  ``telegram``, ``dashboard``, ``cron``, ``explicit`` (orchestrator surfaces —
  ``cron`` is the scheduler surface of a cron-scheduled run; ``explicit`` an
  explicitly-created session on the orchestrator agent, e.g. OpenClaw's
  gateway-fallback path) or ``subagent`` (delegated work). Any other kind on a
  consumed event fails the import loudly rather than silently dropping that
  session's activity.
- ``message.in`` is the inbound operator channel: each event carries the full
  text of a message a human sent the agent mid-run. These are collected as
  ``operator_messages`` so the mapping can stamp the corresponding user turns
  ``source="operator"`` (and surface inbound messages that never entered the
  session thread) — see :func:`events.build_content`.

Intentionally NOT consumed: ``message.sending`` / ``message.out`` (outbound
channel I/O). A sub-agent's final report is auto-announced as a
``message.out`` on the orchestrator's outbound channel, but those events carry
no ``sessionKey``, ``runId``, or ``agentId`` (and the spawn result is only an
``accepted`` ack), so a report cannot be deterministically attributed to the
sub-agent that produced it — file order misleads (reports arrive in completion,
not spawn, order) and only the report text echoing the spawn ``label`` ties the
two together. We therefore do not surface sub-agent reports; see the design doc
``README.md`` ("Known limitations").

The two sub-agent encodings come from OpenClaw, not the telemetry recorder (a
passive forwarder): schema B (activity in ``tool.*`` events) is near-universal,
since the tool hooks fire for every call; schema A (sub-agent turns in ``agent.*
messages[]``, with timestamps + usage) is the richer overlay OpenClaw adds only
when it populates a sub-agent's ``messages[]``. A session may carry A, B, or
both (hybrid); A is authoritative when present.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from logging import getLogger
from typing import Any, Iterable

from inspect_ai.model import Content

from .detection import (
    ORCH_KINDS,
    SUBAGENT_KIND,
    child_session_key_of,
    is_orchestrator,
    session_id_from_session_key,
    session_kind,
)
from .extraction import (
    content_to_text,
    rich_or_text,
    tokens_from_usage,
    toolcalls_of,
)

logger = getLogger(__name__)


@dataclass
class ToolResult:
    """A tool call's result, keyed by ``toolCallId``.

    ``content`` is the result body for the message thread / event: a plain
    string in the common case, or a list of ``Content`` blocks when the result
    carries images (e.g. a screenshot tool). ``text`` is the always-flattened
    text of the same body, kept for the JSON parsing that pulls a spawn's
    ``childSessionKey`` out of its result. ``is_error`` is OpenClaw's
    ``toolResult.isError`` (``None`` when the field is absent) — the
    authoritative success/error signal, keyed exactly by id, so (unlike
    ``tool.end``, which carries no id) it needs no heuristic matching.
    ``timestamp`` is the result's own epoch-ms append time (``None`` when
    absent), used to stamp the ``ToolEvent``'s completion time instead of
    reusing the parent turn's.
    """

    text: str
    content: str | list[Content]
    is_error: bool | None = None
    timestamp: int | None = None


@dataclass
class SubagentSpan:
    """A delegated sub-agent session, anchored to its spawning tool call.

    ``turns`` are the sub-agent's own assistant turn messages (schema A);
    ``tool_calls`` are its ``tool.*`` calls (schema B). Both feed the
    reconstruction of the sub-agent's activity inside its agent span.

    ``anchor_ts`` is the session's *file-order anchor*: the timestamp of the
    latest orchestrator assistant turn seen before the session's first event.
    A session with no linkable spawn call (``spawn_tool_call_id`` is None —
    e.g. cron/system-spawned sub-agents) is placed in the timeline at this
    anchor instead of being dropped; see :func:`events.build_content`.
    """

    session_key: str
    prompt: str | None
    n_tool_calls: int
    n_assistant_turns: int
    spawn_tool_call_id: str | None  # orchestrator toolCall id that spawned it
    spawn_label: str | None  # the spawn's ``label`` arg (used to name the span)
    spawn_task: str | None  # the spawn's ``task`` arg (the delegated instruction)
    turns: list[dict[str, Any]]  # schema-A assistant turns (in file order)
    tool_calls: list[dict[str, Any]]  # schema-B tool.* calls (in file order)
    anchor_ts: int = 0  # latest orchestrator turn ts before first activity


@dataclass
class OpenClawTelemetry:
    """Faithful, consolidated read of one OpenClaw telemetry file.

    The whole-file consolidation (turns deduped, sub-agents reconstructed) lands
    here so the event/message mapping never touches the raw cumulative snapshots.

    ``orchestrator_turns`` are the deduped assistant turns of every
    orchestrator surface (``main``/``telegram``/``dashboard``/``cron``/
    ``explicit``) in timestamp order (each a raw OpenClaw message dict with
    ``content``, ``usage``, ``timestamp``, ``model``). ``compactions`` are the orchestrator's
    real ``compactionSummary`` turns (a sub-agent's own compactions are dropped
    with a warning). ``result_by_callid`` maps a toolCall id to its
    :class:`ToolResult` (text + success/error + completion time).
    ``subagents`` are the delegated sessions. ``user_turns`` are the deduped
    orchestrator ``user`` turns (the human prompts), in timestamp order.

    ``model_name`` is the run's headline model: the most common model across the
    orchestrator turns (see :func:`_primary_model`), or ``None`` when no turn
    records one.

    ``session_id`` is the orchestrator's sessionKey-derived identity — a per-run
    session uuid for ``main``/``dashboard`` surfaces, but a chat id shared across
    runs for ``telegram``. It is therefore NOT unique per run on its own; the
    transcript layer combines it with the run's earliest timestamp.

    ``operator_messages`` are the raw ``message.in`` events (inbound operator
    channel), in file order. The mapping uses them to mark operator-delivered
    user turns ``source="operator"`` and to surface inbound messages that never
    entered the session thread.
    """

    orchestrator_turns: list[dict[str, Any]]
    user_turns: list[dict[str, Any]]
    compactions: list[dict[str, Any]]
    result_by_callid: dict[str, ToolResult]
    model_name: str | None
    subagents: list[SubagentSpan]
    session_id: str | None
    operator_messages: list[dict[str, Any]] = field(default_factory=list)


def _primary_model(orchestrator_turns: list[dict[str, Any]]) -> str | None:
    """The run's headline model: the most common model over orchestrator turns.

    A run may switch models mid-stream, and stray turns can carry a non-model
    tag (e.g. a ``delivery-mirror`` echo), so the modal orchestrator model is a
    more faithful headline than any single turn's. Sub-agent turns are excluded
    on purpose — a sub-agent may run a different model, and it must not become
    the transcript's headline. Ties resolve to the first model seen (turns are
    already in timestamp order). ``parse_telemetry`` guarantees every turn has a
    ``model``; returns ``None`` only when there are no orchestrator turns.
    """
    counts = Counter(str(t["model"]) for t in orchestrator_turns)
    winner = counts.most_common(1)
    return winner[0][0] if winner else None


def _int_or_none(value: Any) -> int | None:
    """Coerce a telemetry numeric field to ``int``, else ``None``.

    Conformant telemetry-hal records integers, but the values come verbatim
    out of ``json.loads``, so a numeric string is coerced and anything else
    yields ``None`` (callers treat that as unclassifiable, never as a match).
    """
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _drop_rollup_aggregates(
    turns: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Drop scaffold roll-up aggregate records from one assembled turn stream.

    OpenClaw's turn-finalization bookkeeping appends an AGGREGATE assistant
    record after a block of per-call records. Its signature — deliberately
    conjunctive, all five conditions — against the previously KEPT turn: no
    ``responseId``, stopReason ``stop``, no toolCalls, a ``totalTokens``
    FROZEN at the previous record's value, and usage that is NOT internally
    consistent. A genuine per-call record satisfies ``input + output +
    cacheRead + cacheWrite == totalTokens`` (verified for every turn across
    the real captures; see :func:`.extraction.usage_to_inspect`), while an
    aggregate's components SUM the block it closes against that stale total,
    breaking the identity. Keeping one double-counts every usage field — ~23M
    phantom ``cache_read`` tokens on one real CRUX capture.

    The consistency condition keeps the genuine turns the frozen-total
    comparison alone would delete on rid-less (service-sink) captures: a
    text-only reply that happens to repeat the previous total, and adjacent
    zero-usage provider-failure placeholders (``0 == 0+0+0+0``).

    ``turns`` must be a SINGLE session's stream: callers group per
    ``sessionKey`` (or per sub-agent session) first, so a turn interleaved
    from another session — another surface, or another concurrent session of
    the same kind — cannot sit between a block's closing record and its
    roll-up and mask the frozen-total comparison.
    """

    def _is_rollup(turn: dict[str, Any], prev: dict[str, Any] | None) -> bool:
        if prev is None or turn.get("responseId") is not None:
            return False
        if (turn.get("stopReason") or "stop") != "stop":
            return False
        if toolcalls_of(turn.get("content")):
            return False
        # Coerce totals before comparing: raw json.loads output can carry a
        # numeric STRING, and an un-coerced comparison would pass the frozen
        # gate ("950" == "950") yet break the int-summed identity below,
        # deleting a genuine turn. Non-numeric totals are unclassifiable.
        usage = turn.get("usage") or {}
        total = _int_or_none(usage.get("totalTokens"))
        prev_total = _int_or_none((prev.get("usage") or {}).get("totalTokens"))
        if total is None or prev_total is None or total != prev_total:
            return False
        # A usage with no component fields gives the identity nothing to
        # classify (its sum is 0 on genuine turns of that shape too): keep —
        # the filter drops only on positive evidence of restated usage.
        if all(
            usage.get(k) is None for k in ("input", "output", "cacheRead", "cacheWrite")
        ):
            return False
        return bool(tokens_from_usage(usage) != total)

    kept: list[dict[str, Any]] = []
    n_rollups = 0
    for turn in turns:
        if _is_rollup(turn, kept[-1] if kept else None):
            n_rollups += 1
            continue
        kept.append(turn)
    if n_rollups:
        logger.info(
            "Dropped %d scaffold roll-up aggregate record(s) whose usage "
            "restates the preceding per-call records",
            n_rollups,
        )
    return kept


def parse_telemetry(raw_events: Iterable[dict[str, Any]]) -> OpenClawTelemetry:
    """Parse raw OpenClaw telemetry events into the consolidated intermediate.

    ``raw_events`` may be any iterable of event dicts (typically the streaming
    reader); it is consumed exactly once.
    """
    c = _consolidate(raw_events)

    # The roll-up filter runs per SESSION: an aggregate closes a block within
    # its own session's message stream, so a turn interleaved from any OTHER
    # session — another surface, or another session of the same kind (real
    # captures carry hundreds of concurrent cron sessions) — must not sit
    # between a block's closing record and its roll-up and mask the
    # frozen-total comparison. Timestamp ties keep file order through the
    # regroup (``_primary_model``'s first-seen tie-break reads this ordering).
    file_order = {id(m): i for i, m in enumerate(c.assistant_by_id.values())}

    def turn_sort_key(m: dict[str, Any]) -> tuple[int, int]:
        return (int(m.get("timestamp") or 0), file_order[id(m)])

    turns_by_session: dict[str, list[dict[str, Any]]] = {}
    for rid, kind in c.assistant_kind.items():
        if is_orchestrator(kind):
            session = c.assistant_session[rid]
            turns_by_session.setdefault(session, []).append(c.assistant_by_id[rid])
    orchestrator_turns = sorted(
        (
            turn
            for session_turns in turns_by_session.values()
            for turn in _drop_rollup_aggregates(
                sorted(session_turns, key=turn_sort_key)
            )
        ),
        key=turn_sort_key,
    )

    # Keyed turns are canonical; a keyless turn whose text matches a keyed one
    # FROM ITS OWN SESSION is that prompt's transient first-snapshot
    # serialization, so drop it — the transient and settled forms are the same
    # session re-serializing its own prompt, so a same-text prompt in another
    # session is a distinct turn. Keyless turns with no keyed twin (runtime
    # context, inter-session messages, keyless human prompts) are kept.
    keyed_texts_by_session: dict[str, set[str]] = {}
    for idem, keyed_turn in c.user_by_idempotency.items():
        keyed_texts_by_session.setdefault(
            c.user_session_by_idempotency[idem], set()
        ).add(content_to_text(keyed_turn.get("content")))
    user_turns = sorted(
        (
            *c.user_by_idempotency.values(),
            *(
                m
                for (user_sk, _ts, _content), m in c.user_by_key.items()
                if content_to_text(m.get("content"))
                not in keyed_texts_by_session.get(user_sk, set())
            ),
        ),
        key=lambda m: int(m.get("timestamp") or 0),
    )

    # Map childSessionKey -> spawning orchestrator toolCall id (from spawn
    # results), and -> the spawn's arguments (``task``/``label``) so the agent
    # span can be named and described from the orchestrator's own view.
    child_to_toolcall: dict[str, str] = {}
    child_to_spawn_args: dict[str, dict[str, Any]] = {}
    for turn in orchestrator_turns:
        for tc in toolcalls_of(turn.get("content")):
            tc_id = tc.get("id")
            if tc_id is None:
                continue
            result = c.result_by_callid.get(tc_id)
            csk = child_session_key_of(result.text) if result else None
            if csk:
                child_to_toolcall[csk] = tc_id
                args = tc.get("arguments")
                child_to_spawn_args[csk] = args if isinstance(args, dict) else {}

    subagents = []
    for sk, s in c.sessions.items():
        # The same scaffold finalizes sub-agent sessions, so their schema-A
        # turns get the same roll-up filter (not yet observed inside real
        # sub-agent sessions — defensive parity with the orchestrator).
        turns = _drop_rollup_aggregates(s.get("turns", []))
        subagents.append(
            SubagentSpan(
                session_key=sk,
                prompt=s.get("prompt"),
                n_tool_calls=s.get("n_tool_calls", 0),
                n_assistant_turns=len(turns)
                if turns
                else s.get("n_assistant_turns", 0),
                spawn_tool_call_id=child_to_toolcall.get(sk),
                spawn_label=(child_to_spawn_args.get(sk) or {}).get("label"),
                spawn_task=(child_to_spawn_args.get(sk) or {}).get("task"),
                turns=turns,
                tool_calls=s.get("tool_calls", []),
                anchor_ts=s.get("anchor_ts", 0),
            )
        )

    # Every assistant turn in valid telemetry-hal records its model. A missing
    # one means malformed / non-telemetry-hal input, so fail here — the single,
    # earliest point holding the assembled turns — with a clear message rather
    # than a bare KeyError deep in event building.
    for turn in (*orchestrator_turns, *(t for sa in subagents for t in sa.turns)):
        if not turn.get("model"):
            raise ValueError(
                "OpenClaw assistant turn is missing its 'model' field; the input "
                "is not valid telemetry-hal (every assistant turn records its model)."
            )

    return OpenClawTelemetry(
        orchestrator_turns=orchestrator_turns,
        user_turns=user_turns,
        compactions=list(c.compactions.values()),
        result_by_callid=c.result_by_callid,
        model_name=_primary_model(orchestrator_turns),
        subagents=subagents,
        session_id=c.session_id,
        operator_messages=c.message_ins,
    )


@dataclass
class _Consolidated:
    """Everything one file-ordered pass over the raw events collects.

    The fields mirror the two former passes (dedup/partition + sub-agent
    extraction) plus the session id, all now gathered together so the stream
    of cumulative snapshots is walked exactly once and never materialized.
    """

    assistant_by_id: dict[Any, dict[str, Any]] = field(default_factory=dict)
    assistant_kind: dict[Any, str] = field(default_factory=dict)
    assistant_session: dict[Any, str] = field(default_factory=dict)
    result_by_callid: dict[str, ToolResult] = field(default_factory=dict)
    compactions: dict[Any, dict[str, Any]] = field(default_factory=dict)
    user_by_idempotency: dict[str, dict[str, Any]] = field(default_factory=dict)
    user_session_by_idempotency: dict[str, str] = field(default_factory=dict)
    user_by_key: dict[Any, dict[str, Any]] = field(default_factory=dict)
    sessions: dict[str, dict[str, Any]] = field(default_factory=dict)
    message_ins: list[dict[str, Any]] = field(default_factory=list)
    session_id: str | None = None


def _keyless_content_json(content: Any) -> str:
    """Serialize a message ``content`` for the keyless dedup key.

    ``toolCall`` ids are masked before serializing: OpenClaw's history
    sanitizer rewrites tool-call ids between cumulative snapshots (observed in
    CRUX1: a turn is first appended with the provider id ``toolu_01...`` and
    every later snapshot re-serializes it as ``toolu01...``, on both the
    ``toolCall`` block and its ``toolResult``). Keying on the raw content would
    keep both spellings of the SAME turn — duplicating its model/tool events
    and double-counting its usage — so the ids must not participate in the key.
    Masking cannot conflate two genuinely different turns: the key still
    carries the timestamp and every other content field.
    """
    if isinstance(content, list):
        content = [
            {**block, "id": ""}
            if isinstance(block, dict) and block.get("type") == "toolCall"
            else block
            for block in content
        ]
    return json.dumps(content, sort_keys=True, default=str)


def _new_session() -> dict[str, Any]:
    """A fresh per-sub-agent-SESSION descriptor (see :func:`_consolidate`)."""
    return {
        "prompt": None,
        "n_assistant_turns": 0,
        "n_tool_calls": 0,
        "turns": [],
        "tool_calls": [],
    }


def _consolidate(raw_events: Iterable[dict[str, Any]]) -> _Consolidated:
    """Single file-ordered streaming pass over the raw events.

    Folds the whole-file consolidation into one walk so a multi-GiB telemetry
    stream is never held in memory: only the deduped turns and sub-agent
    descriptors stay resident. The pass does three things at once, all
    independent and all file-order driven:

    1. Dedup/partition over ``agent.*`` cumulative snapshots. Assistant turns are
       deduped by ``responseId`` (recording each turn's first-occurrence session
       kind), ``toolResult``s by ``toolCallId``, and orchestrator-only
       ``compactionSummary``s and ``user`` turns. Turns and user prompts with no
       ``responseId`` are keyed by ``(session, timestamp, content)`` since they
       recur across their own session's cumulative snapshots.

    2. Sub-agent reconstruction, robust across both export schemas. Schema A: the
       sub-agent's assistant turns live in its own ``agent.* messages[]`` (with
       ``timestamp`` + ``usage``). Schema B: the ``agent.start`` carries only the
       spawn ``prompt`` and activity is in ``tool.*`` events (no timestamps).

    3. The session id: the first orchestrator ``agent.*`` ``sessionKey`` that
       yields a real id.
    """
    out = _Consolidated()
    orch_cursor = 0  # latest orchestrator assistant ts seen so far (file order)
    seen_subagent_rids: set[Any] = set()
    warned_compaction_sessions: set[str] = set()
    for ev in raw_events:
        if not isinstance(ev, dict):
            continue
        t = ev.get("type")
        # The inbound operator channel: collect message.in events whole (they
        # carry no sessionKey — the mapping matches them to user turns by
        # content, see ``events.build_content``).
        if t == "message.in":
            out.message_ins.append(ev)
            continue
        sk = ev.get("sessionKey", "")
        kind = session_kind(sk)
        is_agent = t in ("agent.start", "agent.end")

        # The events the importer consumes must classify as orchestrator or
        # sub-agent. Any other kind — a surface we have not seen (e.g. another
        # chat channel), or an absent/malformed sessionKey — would silently
        # drop that session's activity, so fail loudly instead. (The outbound
        # ``message.sending``/``message.out`` events carry no sessionKey and
        # are intentionally not consumed, so they are not checked.)
        if (is_agent or t in ("tool.start", "tool.end")) and not (
            is_orchestrator(kind) or kind == SUBAGENT_KIND
        ):
            raise ValueError(
                f"OpenClaw telemetry {t!r} event carries sessionKey {sk!r} "
                f"with unrecognized session kind {kind!r} (known kinds: "
                f"{', '.join((*ORCH_KINDS, SUBAGENT_KIND))}). This may be an "
                "OpenClaw surface the importer does not yet support; refusing "
                "to import rather than silently dropping this session's "
                "activity."
            )

        # (3) session id: first orchestrator agent.* key yielding a real id.
        if out.session_id is None and is_agent and is_orchestrator(kind):
            candidate = session_id_from_session_key(sk)
            if candidate:
                out.session_id = candidate

        # (1) dedup/partition over the cumulative messages[] snapshot.
        if is_agent:
            for m in ev.get("messages") or []:
                if not isinstance(m, dict):
                    continue
                role = m.get("role")
                if role == "assistant":
                    rid: Any = m.get("responseId")
                    if rid is None:
                        # No responseId (absent from service-sink captures). Key
                        # by (session, timestamp, id-masked content) so the SAME
                        # turn re-dumped across cumulative snapshots — including
                        # with sanitizer-rewritten toolCall ids — collapses to
                        # one. Re-dumps always come from the turn's own session,
                        # so the session in the key never blocks that collapse;
                        # without it, two GENUINE turns from two concurrent
                        # sessions coinciding on (timestamp, content) would
                        # wrongly merge.
                        rid = (
                            "a",
                            sk,
                            m.get("timestamp"),
                            _keyless_content_json(m.get("content")),
                        )
                    if rid not in out.assistant_by_id:
                        out.assistant_by_id[rid] = m
                        out.assistant_kind[rid] = kind
                        out.assistant_session[rid] = sk
                    if is_orchestrator(kind):
                        # Advance the file-order anchor cursor: sub-agent
                        # sessions first seen after this point anchor here.
                        turn_ts = int(m.get("timestamp") or 0)
                        if turn_ts > orch_cursor:
                            orch_cursor = turn_ts
                elif role == "user" and is_orchestrator(kind):
                    # OpenClaw re-serializes a human prompt across snapshots: a
                    # transient first-snapshot form (no key, structured content)
                    # and a settled form carrying a stable ``idempotencyKey``
                    # (the inbound message id). Dedup keyed turns by that id (the
                    # user-turn analogue of ``responseId``); fall back to
                    # (session, timestamp, content) only for genuinely keyless
                    # turns (runtime context, inter-session messages, and human
                    # prompts that arrived without a key) — session-scoped for
                    # the same reason as the assistant key: re-dumps come from
                    # the turn's own session, while two concurrent sessions can
                    # genuinely coincide on (timestamp, content). The transient
                    # twins are dropped against their own session's keyed set
                    # in ``parse_telemetry``.
                    idem = m.get("idempotencyKey")
                    if idem is not None:
                        if idem not in out.user_by_idempotency:
                            out.user_by_idempotency[idem] = m
                            out.user_session_by_idempotency[idem] = sk
                    else:
                        key = (
                            sk,
                            m.get("timestamp"),
                            json.dumps(m.get("content"), sort_keys=True, default=str),
                        )
                        if key not in out.user_by_key:
                            out.user_by_key[key] = m
                elif role == "toolResult":
                    cid = m.get("toolCallId")
                    if cid is not None and cid not in out.result_by_callid:
                        is_error = m.get("isError")
                        ts = m.get("timestamp")
                        raw = m.get("content", "")
                        out.result_by_callid[cid] = ToolResult(
                            text=content_to_text(raw),
                            content=rich_or_text(raw),
                            is_error=bool(is_error) if is_error is not None else None,
                            timestamp=int(ts) if ts else None,
                        )
                elif role == "compactionSummary":
                    if is_orchestrator(kind):
                        compaction_key = (m.get("timestamp"), "compaction")
                        if compaction_key not in out.compactions:
                            out.compactions[compaction_key] = m
                    elif sk not in warned_compaction_sessions:
                        # A sub-agent compacting its own thread — never observed
                        # in the sample captures (all 467 CRUX1 compactions are
                        # under ``main``), so not worth speculative
                        # reconstruction: drop it, loudly, once per session.
                        warned_compaction_sessions.add(sk)
                        logger.warning(
                            "OpenClaw sub-agent session %s recorded a "
                            "compaction; sub-agent compactions are not "
                            "surfaced (compaction events are only "
                            "reconstructed for the orchestrator).",
                            sk,
                        )

        # (2) sub-agent reconstruction.
        if kind != SUBAGENT_KIND:
            continue
        if sk not in out.sessions:
            out.sessions[sk] = _new_session()
            # File-order anchor: where a session with no linkable spawn call
            # (e.g. cron/system-spawned) is placed in the timeline.
            out.sessions[sk]["anchor_ts"] = orch_cursor
        s = out.sessions[sk]
        if is_agent:
            if t == "agent.start" and ev.get("prompt") and not s["prompt"]:
                s["prompt"] = ev["prompt"]
            for m in ev.get("messages") or []:  # schema-A turns
                if not isinstance(m, dict) or m.get("role") != "assistant":
                    continue
                rid = m.get("responseId")
                if rid is None:
                    # No responseId (absent from service-sink captures: the
                    # datasets that carry a seq/ts envelope). Key by
                    # (session, timestamp, id-masked content) so the SAME turn
                    # re-dumped across cumulative snapshots — including with
                    # sanitizer-rewritten toolCall ids — collapses to one.
                    rid = (
                        "a",
                        sk,
                        m.get("timestamp"),
                        _keyless_content_json(m.get("content")),
                    )
                if rid in seen_subagent_rids:
                    continue
                seen_subagent_rids.add(rid)
                s["n_assistant_turns"] += 1
                s["turns"].append(m)
        elif t == "tool.start":  # schema-B activity
            s["n_tool_calls"] += 1
            # ``ts`` is the telemetry-hal envelope's epoch-ms append time; it is
            # present on the enriched (service-sink) captures and absent on the
            # bare ones, so ``startTs``/``endTs`` may stay None and the mapping
            # falls back to the spawn time.
            s["tool_calls"].append(
                {
                    "toolName": ev.get("toolName"),
                    "params": ev.get("params") or {},
                    "durationMs": None,
                    "success": None,
                    "error": None,
                    "startTs": ev.get("ts"),
                    "endTs": None,
                }
            )
        elif t == "tool.end":  # schema-B activity: fill the matching open call
            # telemetry-hal tool.end events carry toolName but no toolCallId.
            # When same-named calls overlap, pairing an end with a start is
            # inherently heuristic; the reverse scan below keeps the current
            # best-effort convention and may misattribute duration/success in
            # that ambiguous case.
            for call in reversed(s["tool_calls"]):
                if call["durationMs"] is None and call["toolName"] == ev.get(
                    "toolName"
                ):
                    call["durationMs"] = ev.get("durationMs")
                    call["success"] = ev.get("success")
                    # A failed tool.end carries an ``error`` (present exactly when
                    # ``success`` is false); keep it so the ToolEvent can surface
                    # the failure rather than dropping it.
                    call["error"] = ev.get("error")
                    call["endTs"] = ev.get("ts")
                    break
    return out
