"""Tests for the OpenClaw telemetry import source.

Two fixtures cover the two concrete shapes the telemetry takes. They differ
along independent axes — which plugin sink wrote them (so whether events carry a
``seq``/``ts`` envelope), whether assistant turns carry a ``responseId`` (which
dedup key path is used), and how sub-agents are encoded (schema A/B/hybrid) —
not a single format "version". The exact properties of each are documented at
``FIXTURE`` and ``CRUX1_FIXTURE`` below.
"""

from __future__ import annotations

import json
import logging
from collections import Counter
from pathlib import Path
from typing import Any

import pytest
from inspect_ai.event import (
    CompactionEvent,
    Event,
    ModelEvent,
    SpanBeginEvent,
    SpanEndEvent,
    ToolEvent,
)
from inspect_ai.model import (
    ChatMessage,
    ChatMessageAssistant,
    ChatMessageTool,
    ContentImage,
    ContentReasoning,
    ContentText,
)
from inspect_scout import Transcript

from .. import (
    OPENCLAW_TELEMETRY_HAL_SOURCE_TYPE,
    openclaw_telemetry_hal,
)
from ..client import (
    discover_telemetry_files,
    read_telemetry_events,
)
from ..events import build_content
from ..extraction import (
    content_to_text,
    tokens_from_usage,
)
from ..parse import (
    OpenClawTelemetry,
    SubagentSpan,
    parse_telemetry,
)

# Telemetry from the plugin's raw ``appendFileSync`` dump (the pre-service
# payload): events carry ``sessionKey``/``agentId`` but NO ``seq``/``ts``
# envelope, assistant turns carry a ``responseId`` (dedup keys on it), there are
# no ``agent.end`` events, and the three sub-agents are schema B (spawn prompt +
# ``tool.*`` activity only, no turns). Drives orchestrator parsing, agent-span
# nesting, and transcript assembly end to end.
FIXTURE = Path(__file__).parent / "fixtures" / "sample-telemetry.jsonl"

# A tiny hand-carved slice of the CRUX1 eval capture (the real export is ~1GB),
# from the plugin's service sink, chosen for the properties ``FIXTURE`` lacks:
# every event carries the ``seq``/``ts`` envelope, assistant turns have NO
# ``responseId`` (dedup falls back to ``(timestamp, content)``), there are
# ``agent.end`` events, and its single sub-agent is hybrid — the same work
# recorded as BOTH schema-A turns in ``messages[]`` and schema-B ``tool.*``
# events. Image/long-text/markdown bodies are truncated to keep it small.
CRUX1_FIXTURE = Path(__file__).parent / "fixtures" / "crux1-sample-telemetry.jsonl"


async def _transcripts(path: Path) -> list[Transcript]:
    return [t async for t in openclaw_telemetry_hal(path)]


# ``build_content`` returns (events, messages) together; these slice out one side
# for the many tests that assert on only one. Test-only, hence not in the source.
def build_events(parse: OpenClawTelemetry) -> list[Event]:
    return build_content(parse)[0]


def build_messages(parse: OpenClawTelemetry) -> list[ChatMessage]:
    return build_content(parse)[1]


@pytest.fixture
def raw_events() -> list[dict[str, Any]]:
    # read_telemetry_events streams; materialize for tests that iterate it twice.
    return list(read_telemetry_events(FIXTURE))


def _single_transcript() -> Transcript:
    parse_events = read_telemetry_events(FIXTURE)
    from ..transcripts import (
        _create_transcript,
    )

    transcript = _create_transcript(parse_events, FIXTURE)
    assert transcript is not None
    return transcript


class TestDiscovery:
    def test_single_file(self) -> None:
        assert discover_telemetry_files(FIXTURE) == [FIXTURE]

    def test_directory_globs_jsonl(self) -> None:
        found = discover_telemetry_files(FIXTURE.parent)
        assert FIXTURE in found

    def test_tilde_path_expanded(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # The plugin's default output lives under ``~`` (the docs examples use
        # ``~/.openclaw/logs/telemetry.jsonl``), so ``~`` must be expanded.
        monkeypatch.setenv("HOME", str(tmp_path))  # POSIX
        monkeypatch.setenv("USERPROFILE", str(tmp_path))  # Windows
        f = tmp_path / "telemetry.jsonl"
        f.write_text("{}\n")
        assert discover_telemetry_files("~/telemetry.jsonl") == [f]

    def test_nonexistent_path_warns_and_returns_empty(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        missing = tmp_path / "does_not_exist.jsonl"
        with caplog.at_level(logging.WARNING):
            assert discover_telemetry_files(missing) == []
        assert any("does not exist" in r.message.lower() for r in caplog.records)


class TestReadTelemetry:
    def test_reads_all_lines(self, raw_events: list[dict[str, Any]]) -> None:
        assert len(raw_events) > 0
        assert all(isinstance(e, dict) for e in raw_events)

    def test_skips_malformed_lines(self, tmp_path: Path) -> None:
        f = tmp_path / "t.jsonl"
        f.write_text('{"type": "agent.start"}\nnot json\n\n{"type": "agent.end"}\n')
        events = list(read_telemetry_events(f))
        assert len(events) == 2


class TestParse:
    def test_orchestrator_and_subagents(self, raw_events: list[dict[str, Any]]) -> None:
        parse = parse_telemetry(raw_events)
        assert parse.orchestrator_turns
        assert parse.model_name == "claude-opus-4-8"
        assert len(parse.subagents) == 3

    def test_subagents_linked_to_spawn_tool_call(
        self, raw_events: list[dict[str, Any]]
    ) -> None:
        parse = parse_telemetry(raw_events)
        # Every sub-agent in this fixture was spawned via a linkable
        # sessions_spawn tool call (childSessionKey present in the result).
        assert all(sa.spawn_tool_call_id is not None for sa in parse.subagents)

    def test_model_name_ignores_subagent_model(self) -> None:
        # The headline model is the modal ORCHESTRATOR model; a sub-agent running
        # a different model must not become the transcript's model.
        raw = [
            {
                "type": "agent.start",
                "sessionKey": "agent:main:main:s1",
                "messages": [
                    {
                        "role": "assistant",
                        "responseId": "r1",
                        "timestamp": 1,
                        "model": "orch-model",
                        "content": [{"type": "text", "text": "hi"}],
                    }
                ],
            },
            {
                "type": "agent.end",
                "sessionKey": "agent:main:subagent:child-1",
                "messages": [
                    {
                        "role": "assistant",
                        "responseId": "sr1",
                        "timestamp": 2,
                        "model": "subagent-model",
                        "content": [{"type": "text", "text": "sub"}],
                    }
                ],
            },
        ]
        assert parse_telemetry(raw).model_name == "orch-model"

    def test_model_less_turn_fails_with_meaningful_error(self) -> None:
        # Every assistant turn in valid telemetry-hal records its model (0 of
        # ~770k turns across the sample captures lacked one), so a model-less
        # turn means malformed / non-telemetry-hal input. parse_telemetry
        # rejects it with a clear message rather than let a blank model slip
        # through to event building.
        raw = [
            {
                "type": "agent.start",
                "sessionKey": "agent:main:main:s1",
                "messages": [
                    {
                        "role": "assistant",
                        "responseId": "r1",
                        "timestamp": 1,
                        "content": [{"type": "text", "text": "hi"}],
                    }
                ],
            }
        ]
        with pytest.raises(ValueError, match="missing its 'model'"):
            parse_telemetry(raw)

    @pytest.mark.parametrize(
        ("event", "expected_kind"),
        [
            # A surface the importer has not seen (e.g. another chat channel).
            (
                {
                    "type": "agent.start",
                    "sessionKey": "agent:main:discord:guild:12345",
                    "messages": [],
                },
                "discord",
            ),
            # The always-on timing channel from an unrecognized surface.
            (
                {
                    "type": "tool.start",
                    "sessionKey": "agent:main:discord:guild:12345",
                    "toolName": "exec",
                    "params": {},
                },
                "discord",
            ),
            # A consumed event with no sessionKey at all (kind unparseable).
            ({"type": "agent.end", "messages": []}, ""),
        ],
    )
    def test_unrecognized_session_kind_fails_with_meaningful_error(
        self, event: dict[str, Any], expected_kind: str
    ) -> None:
        # A kind outside main/telegram/dashboard/cron/subagent on a consumed event
        # means a session whose turns would otherwise be silently discarded
        # (classified as neither orchestrator nor sub-agent), so the import
        # must fail loudly, naming the kind and the sessionKey.
        with pytest.raises(ValueError, match="unrecognized session kind"):
            parse_telemetry([*self._orch_raw("agent:main:main:s1"), event])
        with pytest.raises(ValueError, match=f"kind {expected_kind!r}"):
            parse_telemetry([*self._orch_raw("agent:main:main:s1"), event])

    def test_explicit_kind_is_orchestrator(self) -> None:
        # OpenClaw's gateway-fallback path opens explicitly-created sessions on
        # the orchestrator agent (sessionKey
        # ``agent:main:explicit:gateway-fallback-<uuid>``; observed carrying the
        # same ``agentId`` as the ``main`` sessions and ordinary main-agent tool
        # activity). Such a session must import as orchestrator activity: its
        # assistant turns join ``orchestrator_turns``, it is NOT reconstructed
        # as a sub-agent, and its always-on ``tool.*`` timing channel is
        # accepted rather than tripping the unrecognized-kind refusal.
        explicit_key = (
            "agent:main:explicit:gateway-fallback-9b603d99-b6c2-477e-b61e-e079f0e8"
        )
        raw = [
            *self._orch_raw("agent:main:main:s1"),
            {
                "type": "agent.start",
                "sessionKey": explicit_key,
                "prompt": "fallback prompt",
                "messages": [
                    {
                        "role": "assistant",
                        "responseId": "r2",
                        "timestamp": 2,
                        "model": "m",
                        "content": [{"type": "text", "text": "via fallback"}],
                    }
                ],
            },
            {
                "type": "tool.start",
                "sessionKey": explicit_key,
                "toolName": "exec",
                "params": {},
            },
            {
                "type": "tool.end",
                "sessionKey": explicit_key,
                "toolName": "exec",
                "durationMs": 5,
                "success": True,
            },
        ]
        parse = parse_telemetry(raw)
        assert [t["responseId"] for t in parse.orchestrator_turns] == ["r1", "r2"]
        assert parse.subagents == []

    def test_message_events_without_session_key_do_not_trip_kind_check(self) -> None:
        # message.* events carry no sessionKey; their missing kind must NOT
        # trip the unrecognized-kind check. message.in is consumed as the
        # inbound operator channel; message.out stays unconsumed.
        raw = [
            {"type": "message.in", "channel": "telegram", "content": "hi"},
            *self._orch_raw("agent:main:main:s1"),
            {"type": "message.out", "channel": "telegram", "content": "bye"},
        ]
        parse = parse_telemetry(raw)
        assert len(parse.orchestrator_turns) == 1
        assert [m["content"] for m in parse.operator_messages] == ["hi"]

    def _orch_raw(self, session_key: str) -> list[dict[str, Any]]:
        return [
            {
                "type": "agent.start",
                "sessionKey": session_key,
                "messages": [
                    {
                        "role": "assistant",
                        "responseId": "r1",
                        "timestamp": 1,
                        "model": "m",
                        "content": [{"type": "text", "text": "hi"}],
                    }
                ],
            }
        ]

    def test_session_id_is_telegram_chat_id(self) -> None:
        # agent:<name>:telegram:<channel>:<chatId> -> the trailing chat id. NB
        # this is a chat id shared across runs, not a per-run id; the transcript
        # layer disambiguates it (see test_transcript_id_disambiguates_chat_id).
        parse = parse_telemetry(
            self._orch_raw("agent:main:telegram:default:direct:5912046256")
        )
        assert parse.session_id == "5912046256"

    def test_session_id_none_for_scrubbed_telegram_key(self) -> None:
        # A redacted trailing id is not a usable id -> None (caller falls back
        # to the file stem).
        parse = parse_telemetry(self._orch_raw("agent:main:telegram:direct:[REMOVED]"))
        assert parse.session_id is None

    def test_session_id_none_for_kind_only_key(self) -> None:
        # agent:main:main carries no id after the kind segment.
        parse = parse_telemetry(self._orch_raw("agent:main:main"))
        assert parse.session_id is None

    @pytest.mark.parametrize(
        "session_key",
        [
            "agent:main:main:s1",
            "agent:main:telegram:default:direct:5912046256",
            "agent:main:dashboard:e6746281-f3cd-4be5-9d0c-633772cdcace",
            "agent:main:cron:5b3f2a10-9c7e-4d21-8e6a-2f1d0c9b8a76",
        ],
    )
    def test_orchestrator_kinds_yield_orchestrator_turns(
        self, session_key: str
    ) -> None:
        # Every orchestrator surface (terminal, Telegram, web dashboard, and
        # the cron scheduler — a cron-scheduled run's orchestrator session
        # carries the ``cron`` kind) must have its assistant turns classified
        # as orchestrator turns; otherwise the import fails on the
        # unrecognized-kind check (or, if it were lenient, the transcript
        # would be silently dropped for having no turns).
        parse = parse_telemetry(self._orch_raw(session_key))
        assert len(parse.orchestrator_turns) == 1

    def test_keyless_turns_with_sanitized_toolcall_ids_collapse(self) -> None:
        # OpenClaw's history sanitizer rewrites toolCall ids between a turn's
        # first snapshot and all later ones (observed in CRUX1: ``toolu_01...``
        # re-serialized as ``toolu01...``, on both the toolCall block and its
        # toolResult). With no responseId to key on, the raw-content fallback
        # key used to keep BOTH spellings of the same turn — duplicating its
        # ModelEvent/ToolEvents, double-counting its usage (~16% of the CRUX1
        # headline total), and re-anchoring sub-agent spans at the twin. The
        # id-masked key must collapse them to one.
        def snapshot(event_type: str, tc_id: str) -> dict[str, Any]:
            return {
                "type": event_type,
                "sessionKey": "agent:main:main",
                "messages": [
                    {
                        "role": "assistant",
                        "timestamp": 1772831311626,
                        "model": "claude-opus-4-6",
                        "usage": {"input": 1, "output": 496, "totalTokens": 497},
                        "content": [
                            {
                                "type": "toolCall",
                                "id": tc_id,
                                "name": "sessions_spawn",
                                "arguments": {"task": "check email", "label": "email"},
                            }
                        ],
                    },
                    {
                        "role": "toolResult",
                        "toolCallId": tc_id,
                        "timestamp": 1772831320863,
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(
                                    {"childSessionKey": "agent:main:subagent:c1"}
                                ),
                            }
                        ],
                    },
                ],
            }

        raw = [
            snapshot("agent.end", "toolu_0131wuKo4St6rSL4BHMNZn2e"),  # first write
            snapshot("agent.start", "toolu0131wuKo4St6rSL4BHMNZn2e"),  # sanitized
            {
                "type": "agent.start",
                "sessionKey": "agent:main:subagent:c1",
                "prompt": "check email",
                "messages": [],
            },
        ]
        parse = parse_telemetry(raw)
        # One turn, kept in its first-seen (provider-id) spelling.
        assert len(parse.orchestrator_turns) == 1
        toolcall_id = parse.orchestrator_turns[0]["content"][0]["id"]
        assert toolcall_id == "toolu_0131wuKo4St6rSL4BHMNZn2e"
        # The spawn links via the kept spelling, whose result is present.
        assert len(parse.subagents) == 1
        assert parse.subagents[0].spawn_tool_call_id == toolcall_id

        events = build_events(parse)
        assert sum(1 for e in events if isinstance(e, ModelEvent)) == 1
        # One agent span, and no stray root-level spawn event from the twin.
        assert sum(1 for e in events if isinstance(e, SpanBeginEvent)) == 1
        assert not [e for e in events if isinstance(e, ToolEvent) and e.span_id is None]

    def test_user_prompt_transient_and_settled_collapse(self) -> None:
        # OpenClaw re-serializes a human prompt across snapshots: a transient
        # first-snapshot form (no idempotencyKey, structured content) and a
        # settled form carrying a stable idempotencyKey. They are one turn and
        # must collapse to the canonical (keyed) copy. A keyless turn with no
        # keyed twin (here a runtime-context injection) is kept.
        sk = "agent:main:dashboard:abc"
        raw = [
            {
                "type": "agent.end",
                "sessionKey": sk,
                "messages": [
                    # transient form: structured content, no key, earlier snapshot
                    {
                        "role": "user",
                        "timestamp": 20,
                        "content": [{"type": "text", "text": "hello there"}],
                    },
                ],
            },
            {
                "type": "agent.start",
                "sessionKey": sk,
                "messages": [
                    # settled form: string content + stable id (same prompt)
                    {
                        "role": "user",
                        "timestamp": 10,
                        "idempotencyKey": "m1:use",
                        "content": "hello there",
                    },
                    # genuine keyless turn, no keyed twin -> kept
                    {"role": "user", "timestamp": 30, "content": "[runtime context]"},
                    {
                        "role": "assistant",
                        "responseId": "r1",
                        "timestamp": 40,
                        "model": "m",
                        "content": [{"type": "text", "text": "hi"}],
                    },
                ],
            },
        ]
        parse = parse_telemetry(raw)
        texts = [content_to_text(u.get("content")) for u in parse.user_turns]
        assert texts == ["hello there", "[runtime context]"]
        kept = parse.user_turns[0]
        # the surviving copy of the prompt is the settled (keyed) one
        assert kept.get("idempotencyKey") == "m1:use"


class TestEvents:
    def test_event_mix(self, raw_events: list[dict[str, Any]]) -> None:
        events = build_events(parse_telemetry(raw_events))
        counts = Counter(e.event for e in events)
        assert counts["model"] > 0
        assert counts["tool"] > 0
        # One begin/end pair per sub-agent.
        assert counts["span_begin"] == 3
        assert counts["span_end"] == 3

    def test_agent_spans_describe_subagents(
        self, raw_events: list[dict[str, Any]]
    ) -> None:
        events = build_events(parse_telemetry(raw_events))
        spans = [e for e in events if isinstance(e, SpanBeginEvent)]
        assert spans and all(s.type == "agent" for s in spans)
        # The span carries the spawn prompt in metadata.
        assert all((s.metadata or {}).get("prompt") for s in spans)
        ends = {e.id for e in events if isinstance(e, SpanEndEvent)}
        assert {s.id for s in spans} == ends

    def test_subagent_activity_reconstructed_inside_span(
        self, raw_events: list[dict[str, Any]]
    ) -> None:
        parse = parse_telemetry(raw_events)
        events = build_events(parse)
        span_ids = {sa.session_key for sa in parse.subagents}
        # The sub-agent's own tool calls are reconstructed as events nested
        # inside its agent span (linked via span_id), not just summarised in
        # the span's metadata.
        nested = [
            e for e in events if isinstance(e, ToolEvent) and e.span_id in span_ids
        ]
        assert nested
        # Schema-B sub-agent work lives in tool.* events: the weather sub-agents
        # each run wttr.in lookups via exec.
        assert any(
            e.function == "exec" and "wttr.in" in str(e.arguments) for e in nested
        )

    def test_subagent_events_nest_under_agent_span_in_tree(
        self, raw_events: list[dict[str, Any]]
    ) -> None:
        from inspect_ai.event import ToolEvent as _ToolEvent
        from inspect_ai.event import event_tree
        from inspect_ai.event._tree import EventTreeSpan

        events = build_events(parse_telemetry(raw_events))
        tree = event_tree(events)

        def agent_spans(nodes: list[Any]) -> list[EventTreeSpan]:
            found: list[EventTreeSpan] = []
            for node in nodes:
                if isinstance(node, EventTreeSpan):
                    if node.type == "agent":
                        found.append(node)
                    found.extend(agent_spans(node.children))
            return found

        spans = agent_spans(tree)
        assert spans
        # Every agent span actually contains the sub-agent's tool events.
        assert all(
            any(isinstance(c, _ToolEvent) for c in span.children) for span in spans
        )

    def test_spawn_tool_folded_into_agent_span(
        self, raw_events: list[dict[str, Any]]
    ) -> None:
        parse = parse_telemetry(raw_events)
        events = build_events(parse)
        spawn_ids = {
            sa.spawn_tool_call_id for sa in parse.subagents if sa.spawn_tool_call_id
        }
        assert spawn_ids
        # Mirroring the Claude Code importer, the spawn call is NOT a root-level
        # tool event; it is folded into its agent span as the span's first child,
        # tagged with agent_span_id so the view renders it as the agent header.
        root_tool_ids = {
            e.id for e in events if isinstance(e, ToolEvent) and e.span_id is None
        }
        assert not (root_tool_ids & spawn_ids)
        for i, e in enumerate(events):
            if isinstance(e, SpanBeginEvent):
                first_child = events[i + 1]
                assert isinstance(first_child, ToolEvent)
                assert first_child.id in spawn_ids
                assert first_child.span_id == e.id
                assert first_child.agent_span_id == e.id

    def test_tool_events_keep_raw_shape(self, raw_events: list[dict[str, Any]]) -> None:
        events = build_events(parse_telemetry(raw_events))
        tool_events = [e for e in events if isinstance(e, ToolEvent)]
        # Raw OpenClaw tool name preserved (no exec->bash relabel).
        assert any(e.function == "exec" for e in tool_events)

    def test_tool_events_carry_result_success_and_completion(
        self, raw_events: list[dict[str, Any]]
    ) -> None:
        # The toolResult's own isError + timestamp are surfaced (keyed exactly by
        # toolCallId, no heuristics): every orchestrator tool event carries a
        # completion time from its result rather than the parent turn's time, so
        # the call->result span is real. This fixture's tools all succeeded.
        events = build_events(parse_telemetry(raw_events))
        root_tools = [
            e for e in events if isinstance(e, ToolEvent) and e.span_id is None
        ]
        assert root_tools
        assert all(e.completed is not None for e in root_tools)
        assert all(e.completed >= e.timestamp for e in root_tools)  # type: ignore[operator]
        assert all(e.failed is False and e.error is None for e in root_tools)
        # The completion time is the result's, distinct from the turn timestamp.
        assert any(e.completed != e.timestamp for e in root_tools)

    def test_errored_tool_result_sets_failed_and_error(self) -> None:
        # isError True -> failed flag + a ToolCallError carrying the result body.
        raw = [
            {
                "type": "agent.start",
                "sessionKey": "agent:run:main:orchestrator",
                "messages": [
                    {
                        "role": "assistant",
                        "responseId": "r1",
                        "timestamp": 1000,
                        "model": "m",
                        "content": [
                            {
                                "type": "toolCall",
                                "id": "tc1",
                                "name": "exec",
                                "arguments": {"command": "nope"},
                            }
                        ],
                    },
                    {
                        "role": "toolResult",
                        "toolCallId": "tc1",
                        "timestamp": 1100,
                        "isError": True,
                        "content": [{"type": "text", "text": "command not found"}],
                    },
                ],
            }
        ]
        events = build_events(parse_telemetry(raw))
        tool = next(e for e in events if isinstance(e, ToolEvent))
        assert tool.failed is True
        assert tool.error is not None and tool.error.message == "command not found"
        assert tool.result == "command not found"

    def test_stop_reason_mapped_from_recorded_value(self) -> None:
        # The recorded ``stopReason`` drives the model event's stop reason -- it
        # is NOT re-derived from whether tool calls were parsed. An errored turn
        # maps to ``unknown`` and propagates its ``errorMessage``; a length turn
        # to ``max_tokens``; a normal turn to ``stop``; a toolUse turn (even one
        # whose content happens to carry no toolCall block) to ``tool_calls``.
        def turn(rid: str, ts: int, reason: str, **extra: Any) -> dict[str, Any]:
            return {
                "role": "assistant",
                "responseId": rid,
                "timestamp": ts,
                "model": "m",
                "content": [{"type": "text", "text": rid}],
                "stopReason": reason,
                **extra,
            }

        raw = [
            {
                "type": "agent.start",
                "sessionKey": "agent:run:main:orchestrator",
                "messages": [
                    turn("r1", 1000, "stop"),
                    turn("r2", 1001, "toolUse"),
                    turn("r3", 1002, "length"),
                    turn("r4", 1003, "error", errorMessage="overloaded"),
                ],
            }
        ]
        events = build_events(parse_telemetry(raw))
        model_events = [e for e in events if isinstance(e, ModelEvent)]
        reasons = [e.output.stop_reason for e in model_events]
        assert reasons == ["stop", "tool_calls", "max_tokens", "unknown"]
        errored = model_events[-1]
        assert errored.error == "overloaded"
        assert errored.output.error == "overloaded"
        # Non-errored turns carry no error.
        assert all(e.error is None for e in model_events[:-1])

    def test_subagent_compaction_dropped_with_warning(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        # A compactionSummary inside a SUB-AGENT's snapshot is that sub-agent's
        # own thread compacting — it must NOT surface as a root-level
        # CompactionEvent in the orchestrator timeline. Never observed in the
        # sample captures (all of CRUX1's 467 compactions are under ``main``),
        # so it is dropped with a warning — once per session, even though
        # cumulative snapshots re-dump it — rather than reconstructed
        # speculatively. The orchestrator's own compaction is still emitted.
        spawn_id = "tc_spawn"
        child = "agent:run:subagent:child-1"
        subagent_messages: list[dict[str, Any]] = [
            {
                "role": "assistant",
                "responseId": "sr1",
                "timestamp": 1100,
                "model": "claude-x",
                "content": [{"type": "text", "text": "sub work"}],
            },
            {
                "role": "compactionSummary",
                "timestamp": 1200,
                "tokensBefore": 999,
            },
        ]
        raw: list[dict[str, Any]] = [
            {
                "type": "agent.start",
                "sessionKey": "agent:run:main:orchestrator",
                "messages": [
                    {
                        "role": "assistant",
                        "responseId": "r1",
                        "timestamp": 1000,
                        "model": "claude-x",
                        "content": [
                            {
                                "type": "toolCall",
                                "id": spawn_id,
                                "name": "sessions_spawn",
                                "arguments": {"task": "delegate"},
                            }
                        ],
                    },
                    {
                        "role": "toolResult",
                        "toolCallId": spawn_id,
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps({"childSessionKey": child}),
                            }
                        ],
                    },
                    {
                        "role": "compactionSummary",
                        "timestamp": 2000,
                        "tokensBefore": 111,
                    },
                ],
            },
            # Two cumulative snapshots re-dumping the same sub-agent compaction.
            {
                "type": "agent.start",
                "sessionKey": child,
                "prompt": "sub task",
                "messages": subagent_messages,
            },
            {
                "type": "agent.end",
                "sessionKey": child,
                "messages": subagent_messages,
            },
        ]
        with caplog.at_level(logging.WARNING):
            parse = parse_telemetry(raw)
        # Only the orchestrator's compaction survives, and the drop is reported
        # once, naming the sub-agent session.
        assert [c.get("tokensBefore") for c in parse.compactions] == [111]
        warnings = [
            r
            for r in caplog.records
            if "compaction" in r.getMessage() and child in r.getMessage()
        ]
        assert len(warnings) == 1
        compaction_events = [
            e for e in build_events(parse) if isinstance(e, CompactionEvent)
        ]
        assert len(compaction_events) == 1
        assert compaction_events[0].tokens_before == 111

    def test_model_events_carry_usage(self, raw_events: list[dict[str, Any]]) -> None:
        events = build_events(parse_telemetry(raw_events))
        model_events = [e for e in events if isinstance(e, ModelEvent)]
        assert model_events
        assert any(
            e.output.usage and e.output.usage.output_tokens > 0 for e in model_events
        )

    def test_model_event_input_carries_conversation(
        self, raw_events: list[dict[str, Any]]
    ) -> None:
        events = build_events(parse_telemetry(raw_events))
        model_events = [e for e in events if isinstance(e, ModelEvent)]
        # The first model call's input is the opening user prompt; later calls
        # accumulate the conversation (so user turns show in the events view).
        assert model_events[0].input and model_events[0].input[0].role == "user"
        assert any("user" in {m.role for m in e.input} for e in model_events)
        assert len(model_events[-1].input) > len(model_events[0].input)

    def test_model_output_preserves_tool_calls(
        self, raw_events: list[dict[str, Any]]
    ) -> None:
        events = build_events(parse_telemetry(raw_events))
        model_events = [e for e in events if isinstance(e, ModelEvent)]
        assert any(e.output.message.tool_calls for e in model_events)

    def test_model_events_attributed_per_turn(self) -> None:
        # Each ModelEvent is attributed to its own turn's ``model`` verbatim --
        # including a stray non-model tag (OpenClaw emits a ``delivery-mirror``
        # echo on occasional turns). The headline model, by contrast, is the
        # MODAL orchestrator model, so it ignores the stray tag.
        raw = [
            {
                "type": "agent.start",
                "sessionKey": "agent:main:main:s1",
                "messages": [
                    {
                        "role": "assistant",
                        "responseId": "r1",
                        "timestamp": 1,
                        "model": "model-a",
                        "content": [{"type": "text", "text": "one"}],
                    },
                    {
                        "role": "assistant",
                        "responseId": "r2",
                        "timestamp": 2,
                        "model": "delivery-mirror",
                        "content": [{"type": "text", "text": "two"}],
                    },
                    {
                        "role": "assistant",
                        "responseId": "r3",
                        "timestamp": 3,
                        "model": "model-a",
                        "content": [{"type": "text", "text": "three"}],
                    },
                ],
            }
        ]
        parse = parse_telemetry(raw)
        assert parse.model_name == "model-a"  # modal, ignores the stray tag
        events = build_events(parse)
        models = [e.model for e in events if isinstance(e, ModelEvent)]
        # Each event keeps its own raw model tag -- no fallback, no rewriting.
        assert models == ["model-a", "delivery-mirror", "model-a"]


class TestSchemaASubagents:
    """Schema-A sub-agents carry their own turns inside ``agent.* messages[]``.

    Synthetic fixture (the bundled sample is schema B): one orchestrator turn
    spawns a sub-agent whose assistant turn + tool result live in its own
    ``agent.start`` snapshot, with usage and timestamps.
    """

    def _raw(self) -> list[dict[str, Any]]:
        spawn_id = "tc_spawn"
        child = "agent:run:subagent:child-1"
        return [
            {
                "type": "agent.start",
                "sessionKey": "agent:run:main:orchestrator",
                "messages": [
                    {
                        "role": "assistant",
                        "responseId": "r1",
                        "timestamp": 1000,
                        "model": "claude-x",
                        "content": [
                            {
                                "type": "toolCall",
                                "id": spawn_id,
                                "name": "sessions_spawn",
                                "arguments": {"task": "delegate"},
                            }
                        ],
                    },
                    {
                        "role": "toolResult",
                        "toolCallId": spawn_id,
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps({"childSessionKey": child}),
                            }
                        ],
                    },
                ],
            },
            {
                "type": "agent.start",
                "sessionKey": child,
                "prompt": "sub task",
                "messages": [
                    {
                        "role": "assistant",
                        "responseId": "sr1",
                        "timestamp": 1100,
                        "model": "claude-x",
                        "usage": {"input": 10, "output": 20},
                        "content": [
                            {"type": "text", "text": "sub thinking"},
                            {
                                "type": "toolCall",
                                "id": "stc1",
                                "name": "exec",
                                "arguments": {"command": "ls"},
                            },
                        ],
                    },
                    {
                        "role": "toolResult",
                        "toolCallId": "stc1",
                        "content": [{"type": "text", "text": "file.txt"}],
                    },
                ],
            },
        ]

    def test_turns_become_model_and_tool_events_in_span(self) -> None:
        parse = parse_telemetry(self._raw())
        events = build_events(parse)
        span_ids = {sa.session_key for sa in parse.subagents}
        # Sub-agent assistant turn -> ModelEvent nested in the agent span.
        model_in_span = [
            e for e in events if isinstance(e, ModelEvent) and e.span_id in span_ids
        ]
        assert model_in_span
        assert model_in_span[0].output.usage
        assert model_in_span[0].output.usage.output_tokens == 20
        # Sub-agent tool call -> ToolEvent nested in the span, with its result.
        tool_in_span = [
            e for e in events if isinstance(e, ToolEvent) and e.span_id in span_ids
        ]
        assert any(
            e.function == "exec" and e.result == "file.txt" for e in tool_in_span
        )
        span_end = next(e for e in events if isinstance(e, SpanEndEvent))
        children = [
            e
            for e in events
            if isinstance(e, (ModelEvent, ToolEvent)) and e.span_id == span_end.id
        ]
        assert all(span_end.timestamp >= e.timestamp for e in children)
        assert all(
            span_end.timestamp >= e.completed
            for e in children
            if e.completed is not None
        )

    def test_subagent_turns_excluded_from_main_thread(self) -> None:
        messages = build_messages(parse_telemetry(self._raw()))
        # The orchestrator spawn turn is on the main thread; the sub-agent's
        # own "sub thinking" turn is not.
        assert not any("sub thinking" in m.text for m in messages)

    def test_keyless_turns_dedupe_across_snapshots(self) -> None:
        # A schema-A sub-agent turn with no responseId (service-sink captures
        # strip it) that recurs across the sub-agent's cumulative agent.*
        # snapshots must collapse to one, exactly as the orchestrator path
        # dedupes its keyless turns. Regression: the sub-agent path used to
        # dedupe only keyed turns, so a keyless turn re-dumped across snapshots
        # was double-counted (inflating n_assistant_turns, span ModelEvents,
        # and the headline token total).
        spawn_id = "tc_spawn"
        child = "agent:run:subagent:child-1"
        turn: dict[str, Any] = {
            "role": "assistant",
            "timestamp": 1100,
            "model": "claude-x",
            "usage": {"input": 10, "output": 20},
            "content": [{"type": "text", "text": "keyless work"}],
        }
        raw: list[dict[str, Any]] = [
            {
                "type": "agent.start",
                "sessionKey": "agent:run:main:orchestrator",
                "messages": [
                    {
                        "role": "assistant",
                        "responseId": "r1",
                        "timestamp": 1000,
                        "model": "claude-x",
                        "content": [
                            {
                                "type": "toolCall",
                                "id": spawn_id,
                                "name": "sessions_spawn",
                                "arguments": {"task": "delegate"},
                            }
                        ],
                    },
                    {
                        "role": "toolResult",
                        "toolCallId": spawn_id,
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps({"childSessionKey": child}),
                            }
                        ],
                    },
                ],
            },
            # Two populated snapshots for the sub-agent, each re-dumping the same
            # keyless turn (agent.start then a later agent.end).
            {"type": "agent.start", "sessionKey": child, "messages": [turn]},
            {"type": "agent.end", "sessionKey": child, "messages": [turn]},
        ]
        parse = parse_telemetry(raw)
        assert len(parse.subagents) == 1
        sa = parse.subagents[0]
        assert sa.n_assistant_turns == 1
        assert len(sa.turns) == 1

    def test_keyless_turns_with_sanitized_toolcall_ids_collapse(self) -> None:
        # The sub-agent analogue of the orchestrator sanitized-id test: a
        # keyless schema-A turn re-dumped with rewritten toolCall ids must
        # collapse to one turn, keyed on the id-masked content.
        spawn_id = "tc_spawn"
        child = "agent:run:subagent:child-1"

        def turn(tc_id: str) -> dict[str, Any]:
            return {
                "role": "assistant",
                "timestamp": 1100,
                "model": "claude-x",
                "usage": {"input": 10, "output": 20},
                "content": [
                    {
                        "type": "toolCall",
                        "id": tc_id,
                        "name": "exec",
                        "arguments": {"command": "ls"},
                    }
                ],
            }

        raw: list[dict[str, Any]] = [
            {
                "type": "agent.start",
                "sessionKey": "agent:run:main:orchestrator",
                "messages": [
                    {
                        "role": "assistant",
                        "responseId": "r1",
                        "timestamp": 1000,
                        "model": "claude-x",
                        "content": [
                            {
                                "type": "toolCall",
                                "id": spawn_id,
                                "name": "sessions_spawn",
                                "arguments": {"task": "delegate"},
                            }
                        ],
                    },
                    {
                        "role": "toolResult",
                        "toolCallId": spawn_id,
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps({"childSessionKey": child}),
                            }
                        ],
                    },
                ],
            },
            {
                "type": "agent.start",
                "sessionKey": child,
                "messages": [turn("toolu_01AbC")],
            },
            {
                "type": "agent.end",
                "sessionKey": child,
                "messages": [turn("toolu01AbC")],  # sanitized re-dump
            },
        ]
        parse = parse_telemetry(raw)
        assert len(parse.subagents) == 1
        sa = parse.subagents[0]
        assert sa.n_assistant_turns == 1
        assert len(sa.turns) == 1
        assert sa.turns[0]["content"][0]["id"] == "toolu_01AbC"  # first-seen kept

    def test_hybrid_does_not_double_count_tool_calls(self) -> None:
        # Hybrid sub-agent: the SAME calls are recorded twice -- once as
        # toolCall blocks in messages[] (schema A, with results) and again as
        # tool.* events (schema B, no results). The schema-A turns are
        # authoritative, so tool.* must not be re-emitted.
        child = "agent:run:subagent:child-1"
        raw = self._raw() + [
            {
                "type": "tool.start",
                "sessionKey": child,
                "toolName": "exec",
                "params": {"command": "ls"},
            },
            {
                "type": "tool.end",
                "sessionKey": child,
                "toolName": "exec",
                "durationMs": 5,
                "success": True,
            },
        ]
        parse = parse_telemetry(raw)
        events = build_events(parse)
        span_ids = {sa.session_key for sa in parse.subagents}
        exec_events = [
            e
            for e in events
            if isinstance(e, ToolEvent)
            and e.span_id in span_ids
            and e.function == "exec"
        ]
        # Exactly one exec event (from the schema-A turn), carrying its result.
        assert len(exec_events) == 1
        assert exec_events[0].result == "file.txt"

    def test_unlinked_subagent_placed_not_dropped(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        # A sub-agent whose spawn cannot be linked to a tool call (no
        # childSessionKey resolvable to a spawn call) is placed by its
        # file-order anchor with an info log, not dropped — cron/system-spawned
        # sessions have no spawn call at all. Placement order and the
        # no-fabricated-spawn invariant are locked in TestSpawnlessSubagents.
        child = "agent:run:subagent:orphan-1"
        raw = [
            {
                "type": "agent.start",
                "sessionKey": "agent:run:main:orchestrator",
                "messages": [
                    {
                        "role": "assistant",
                        "responseId": "r1",
                        "timestamp": 1000,
                        "model": "claude-x",
                        "content": [{"type": "text", "text": "hi"}],
                    }
                ],
            },
            {
                "type": "agent.start",
                "sessionKey": child,
                "prompt": "orphan task",
                "messages": [
                    {
                        "role": "assistant",
                        "responseId": "sr1",
                        "timestamp": 1100,
                        "model": "claude-x",
                        "content": [{"type": "text", "text": "orphan work"}],
                    }
                ],
            },
        ]
        parse = parse_telemetry(raw)
        assert len(parse.subagents) == 1
        assert parse.subagents[0].spawn_tool_call_id is None
        with caplog.at_level(logging.INFO):
            events = build_events(parse)
        # The unlinked sub-agent still gets its agent span, and is reported.
        span = next(e for e in events if isinstance(e, SpanBeginEvent))
        assert span.id == child
        assert any(
            "file-order anchor" in r.getMessage() and child in r.getMessage()
            for r in caplog.records
        )


class TestSchemaBSubagents:
    """Schema-B sub-agents record activity only in ``tool.*`` events.

    Synthetic fixture: one orchestrator turn spawns a sub-agent whose work is a
    single ``tool.start``/``tool.end`` pair (no ``messages[]`` turns), matching
    the enriched envelope's ``ts``/``error`` fields.
    """

    def _raw(self, *, success: bool, ts: bool) -> list[dict[str, Any]]:
        spawn_id = "tc_spawn"
        child = "agent:run:subagent:child-1"
        start: dict[str, Any] = {
            "type": "tool.start",
            "sessionKey": child,
            "toolName": "exec",
            "params": {"command": "wttr.in"},
        }
        end: dict[str, Any] = {
            "type": "tool.end",
            "sessionKey": child,
            "toolName": "exec",
            "durationMs": 250,
            "success": success,
        }
        if ts:
            start["ts"] = 5000
            end["ts"] = 5250
        if not success:
            end["error"] = "Error: HTTP 404"
        return [
            {
                "type": "agent.start",
                "sessionKey": "agent:run:main:orchestrator",
                "messages": [
                    {
                        "role": "assistant",
                        "responseId": "r1",
                        "timestamp": 1000,
                        "model": "m",
                        "stopReason": "toolUse",
                        "content": [
                            {
                                "type": "toolCall",
                                "id": spawn_id,
                                "name": "sessions_spawn",
                                "arguments": {"task": "get weather", "label": "wx"},
                            }
                        ],
                    },
                    {
                        "role": "toolResult",
                        "toolCallId": spawn_id,
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps({"childSessionKey": child}),
                            }
                        ],
                    },
                ],
            },
            {"type": "agent.start", "sessionKey": child, "prompt": "get weather"},
            start,
            end,
        ]

    def _tool_event(self, events: list[Event]) -> ToolEvent:
        span_ids = {e.id for e in events if isinstance(e, SpanBeginEvent)}
        return next(
            e
            for e in events
            if isinstance(e, ToolEvent)
            and e.span_id in span_ids
            and e.function == "exec"
        )

    def test_schema_b_tool_events_use_recorded_timestamps(self) -> None:
        # The tool.*'s own ``ts`` gives the call a real start->end span rather
        # than collapsing it to the spawn time (zero duration).
        events = build_events(parse_telemetry(self._raw(success=True, ts=True)))
        tool = self._tool_event(events)
        assert tool.completed is not None
        assert tool.completed > tool.timestamp
        # The agent span ends at the child's real end time, not the spawn ack.
        span_end = next(e for e in events if isinstance(e, SpanEndEvent))
        assert span_end.timestamp >= tool.completed

    def test_schema_b_missing_ts_derives_width_from_duration_ms(self) -> None:
        # Bare captures carry no ``ts``: the call is stamped at the spawn time,
        # and ``durationMs`` (from tool.end) still gives it a real start->end
        # width — downstream busy-time sums rely on it.
        events = build_events(parse_telemetry(self._raw(success=True, ts=False)))
        tool = self._tool_event(events)
        assert tool.completed is not None
        assert (tool.completed - tool.timestamp).total_seconds() == 0.25
        # The agent span still ends at the call's derived end time.
        span_end = next(e for e in events if isinstance(e, SpanEndEvent))
        assert span_end.timestamp >= tool.completed

    def test_schema_b_missing_ts_and_duration_collapses_to_zero(self) -> None:
        # Only a call with neither ``ts`` nor ``durationMs`` collapses to the
        # spawn time (zero duration) rather than failing.
        raw = self._raw(success=True, ts=False)
        end = next(e for e in raw if e.get("type") == "tool.end")
        del end["durationMs"]
        events = build_events(parse_telemetry(raw))
        tool = self._tool_event(events)
        assert tool.completed == tool.timestamp

    def test_schema_b_malformed_duration_ms_survives(self) -> None:
        # ``durationMs`` comes verbatim out of json.loads: a numeric string
        # still yields a width; a non-numeric or negative value degrades to
        # zero width — never a TypeError that aborts the whole import (and a
        # negative never places ``completed`` before ``timestamp``).
        for bad, width in (("250", 0.25), ("bogus", 0.0), (-500, 0.0)):
            raw = self._raw(success=True, ts=False)
            end = next(e for e in raw if e.get("type") == "tool.end")
            end["durationMs"] = bad
            events = build_events(parse_telemetry(raw))
            tool = self._tool_event(events)
            assert tool.completed is not None
            assert (tool.completed - tool.timestamp).total_seconds() == width

    def test_schema_b_tool_failure_surfaced(self) -> None:
        # A tool.end with success=false is a real failure: the standard
        # failed/error fields are populated (not left None) and carry the
        # recorded error message.
        events = build_events(parse_telemetry(self._raw(success=False, ts=True)))
        tool = self._tool_event(events)
        assert tool.failed is True
        assert tool.error is not None and tool.error.message == "Error: HTTP 404"
        # ``success`` is still kept in metadata alongside the standard fields.
        assert (tool.metadata or {}).get("success") is False

    def test_schema_b_tool_success_sets_failed_false(self) -> None:
        events = build_events(parse_telemetry(self._raw(success=True, ts=True)))
        tool = self._tool_event(events)
        assert tool.failed is False
        assert tool.error is None


class TestSpawnlessSubagents:
    """Sub-agent sessions with no linkable ``sessions_spawn`` call.

    Cron/system-spawned sessions (a normal OpenClaw pattern on scheduled runs;
    46 of 101 sub-agent sessions on a real cron-scheduled CRUX capture) appear
    in the telemetry with no spawn tool call at all. They are placed at their
    file-order anchor — the latest orchestrator turn seen before the session's
    first event — with no spawn call fabricated, instead of being dropped.
    """

    CHILD = "agent:main:subagent:cron-child-1"
    PROMPT = (
        "[Subagent Context] You are a subagent spawned by the main agent.\n"
        "You are running as a subagent. Report back when done.\n"
        "Run the ablation sweep for setting X.\n"
        "Include the smaller grids first."
    )

    def _turn(self, rid: str, ts: int, text: str) -> dict[str, Any]:
        return {
            "role": "assistant",
            "responseId": rid,
            "timestamp": ts,
            "model": "m",
            "content": [{"type": "text", "text": text}],
        }

    def _raw(self) -> list[dict[str, Any]]:
        orch = "agent:main:cron:orchestrator"
        a1, a2, a3 = (
            self._turn("r1", 1000, "A1"),
            self._turn("r2", 2000, "A2"),
            self._turn("r3", 3000, "A3"),
        )
        return [
            # First snapshot: A1 + A2 precede the sub-agent in file order.
            {"type": "agent.start", "sessionKey": orch, "messages": [a1, a2]},
            {"type": "agent.start", "sessionKey": self.CHILD, "prompt": self.PROMPT},
            {
                "type": "tool.start",
                "sessionKey": self.CHILD,
                "toolName": "exec",
                "params": {"command": "run sweep"},
            },
            {
                "type": "tool.end",
                "sessionKey": self.CHILD,
                "toolName": "exec",
                "durationMs": 100,
                "success": True,
            },
            # Later cumulative snapshot appends A3 after the sub-agent appeared.
            {"type": "agent.end", "sessionKey": orch, "messages": [a1, a2, a3]},
        ]

    def test_placed_at_file_order_anchor(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        parse = parse_telemetry(self._raw())
        assert len(parse.subagents) == 1
        assert parse.subagents[0].spawn_tool_call_id is None
        # The anchor is A2's timestamp: the latest orchestrator turn seen (in
        # file order) before the session's first event.
        assert parse.subagents[0].anchor_ts == 2000
        with caplog.at_level(logging.INFO):
            events = build_events(parse)
        # Placed immediately AFTER its anchor turn A2 (the latest orchestrator
        # turn seen, in file order, before the session's first event): the
        # orchestrator had already produced A2 when the session appeared, so
        # the span belongs on A2's far side. Reported at info level.
        span = next(e for e in events if isinstance(e, SpanBeginEvent))
        roots = [e for e in events if isinstance(e, ModelEvent)]
        assert events.index(span) == events.index(roots[1]) + 1
        assert any(
            "file-order anchor" in r.getMessage() and self.CHILD in r.getMessage()
            for r in caplog.records
        )

    def test_no_spawn_tool_call_fabricated(self) -> None:
        events = build_events(parse_telemetry(self._raw()))
        # No spawn call was recorded, so none is folded into the span — but the
        # session's own activity is still reconstructed inside it.
        folded = [
            e
            for e in events
            if isinstance(e, ToolEvent) and e.agent_span_id == self.CHILD
        ]
        assert folded == []
        inner = [
            e for e in events if isinstance(e, ToolEvent) and e.span_id == self.CHILD
        ]
        assert [e.function for e in inner] == ["exec"]

    def test_span_named_from_prompt_task_line(self) -> None:
        # No spawn label exists, so the span is named from the first
        # task-bearing line of the session's own prompt, skipping OpenClaw's
        # "[Subagent Context] …" / "You are running as a subagent…" preamble.
        events = build_events(parse_telemetry(self._raw()))
        span = next(e for e in events if isinstance(e, SpanBeginEvent))
        assert span.name == "Run the ablation sweep for setting X."

    def test_anchor_at_run_start_places_before_first_turn(self) -> None:
        # A session first seen before ANY orchestrator turn anchors at 0 and is
        # emitted ahead of the first turn rather than lost.
        raw = self._raw()
        raw.insert(0, raw.pop(1))  # move the sub-agent's agent.start first
        parse = parse_telemetry(raw)
        assert parse.subagents[0].anchor_ts == 0
        events = build_events(parse)
        span = next(e for e in events if isinstance(e, SpanBeginEvent))
        first_model = next(e for e in events if isinstance(e, ModelEvent))
        assert events.index(span) < events.index(first_model)

    def test_anchor_flush_precedes_interleaved_compaction(self) -> None:
        # The anchor flush runs on every timeline item, so a span anchored
        # before a compaction is emitted before that compaction, not swept
        # past it to the next assistant turn.
        orch = "agent:main:cron:orchestrator"
        raw: list[dict[str, Any]] = [
            {
                "type": "agent.start",
                "sessionKey": orch,
                "messages": [self._turn("r1", 1000, "A1")],
            },
            {"type": "agent.start", "sessionKey": self.CHILD, "prompt": self.PROMPT},
            {
                "type": "tool.start",
                "sessionKey": self.CHILD,
                "toolName": "exec",
                "params": {},
            },
            {
                "type": "agent.end",
                "sessionKey": orch,
                "messages": [
                    self._turn("r1", 1000, "A1"),
                    {
                        "role": "compactionSummary",
                        "timestamp": 1500,
                        "tokensBefore": 100,
                    },
                    self._turn("r2", 2000, "A2"),
                ],
            },
        ]
        events = build_events(parse_telemetry(raw))
        span = next(e for e in events if isinstance(e, SpanBeginEvent))
        compaction = next(e for e in events if isinstance(e, CompactionEvent))
        assert events.index(span) < events.index(compaction)

    def test_span_named_from_inline_subagent_task_tag(self) -> None:
        # The fixture-shaped prompt announces the task INLINE after the
        # "[Subagent Task]:" tag. The tag is authoritative — it must not be
        # skipped as bracket boilerplate (which named the span from the later
        # report-back line instead).
        raw = self._raw()
        raw[1] = dict(
            raw[1],
            prompt=(
                "[Fri 2026-03-06 13:08 PST] [Subagent Context] You are running "
                "as a subagent (depth 1/1). Results auto-announce to your "
                "requester; do not busy-poll for status.\n"
                "\n"
                "[Subagent Task]: Check the unread queue\n"
                "\n"
                "Report back with anything unread."
            ),
        )
        events = build_events(parse_telemetry(raw))
        span = next(e for e in events if isinstance(e, SpanBeginEvent))
        assert span.name == "Check the unread queue"

    def test_span_named_from_line_after_bare_task_tag(self) -> None:
        # The tag alone on its line: the task is the next non-empty line.
        raw = self._raw()
        raw[1] = dict(
            raw[1],
            prompt=(
                "[Subagent Context] You are running as a subagent.\n"
                "[Subagent Task]\n"
                "Run the smaller grids first.\n"
                "Then report back."
            ),
        )
        events = build_events(parse_telemetry(raw))
        span = next(e for e in events if isinstance(e, SpanBeginEvent))
        assert span.name == "Run the smaller grids first."

    def test_duplicate_spawn_claim_warns_and_places_by_anchor(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        # A second session claiming an already-claimed spawn call violates the
        # documented 1:1 spawn->session mapping (corrupt/ambiguous linkage).
        # It is anchor-placed like a spawn-less session, but the anomaly must
        # surface at WARNING level — the normal cron pattern stays at info.
        turn = {
            "role": "assistant",
            "responseId": "r1",
            "timestamp": 1000,
            "model": "m",
            "content": [
                {"type": "text", "text": "spawning"},
                {
                    "type": "toolCall",
                    "id": "tc1",
                    "name": "sessions_spawn",
                    "arguments": {"label": "one"},
                },
            ],
        }

        def span_for(key: str) -> SubagentSpan:
            return SubagentSpan(
                session_key=key,
                prompt=None,
                n_tool_calls=0,
                n_assistant_turns=0,
                spawn_tool_call_id="tc1",
                spawn_label="one",
                spawn_task=None,
                turns=[],
                tool_calls=[],
                anchor_ts=1000,
            )

        parse = OpenClawTelemetry(
            orchestrator_turns=[turn],
            user_turns=[],
            compactions=[],
            result_by_callid={},
            model_name="m",
            subagents=[
                span_for("agent:main:subagent:claim-1"),
                span_for("agent:main:subagent:claim-2"),
            ],
            session_id="s",
        )
        with caplog.at_level(logging.WARNING):
            events = build_events(parse)
        spans = {e.id for e in events if isinstance(e, SpanBeginEvent)}
        assert spans == {
            "agent:main:subagent:claim-1",
            "agent:main:subagent:claim-2",
        }
        assert any(
            r.levelno == logging.WARNING
            and "already claimed" in r.getMessage()
            and "agent:main:subagent:claim-2" in r.getMessage()
            for r in caplog.records
        )


class TestRollupAggregates:
    """Scaffold roll-up aggregate records are dropped, not double-counted.

    OpenClaw's turn-finalization bookkeeping appends an aggregate assistant
    record after a block of per-call records: no ``responseId``, stopReason
    ``stop``, no toolCalls, ``totalTokens`` frozen at the previous record's
    value, and usage components that SUM the block (breaking the per-call
    identity ``input + output + cacheRead + cacheWrite == totalTokens``).
    Keeping it double-counts every usage field (~23M phantom cache-read tokens
    on one real CRUX capture). The filter runs per orchestrator surface and
    per sub-agent session, so interleaving cannot mask the comparison.
    """

    ORCH = "agent:main:cron:orchestrator"

    def _turn(
        self,
        *,
        rid: str | None,
        ts: int,
        text: str,
        usage: dict[str, int],
        stop: str = "stop",
        tool_call: bool = False,
    ) -> dict[str, Any]:
        content: list[dict[str, Any]] = [{"type": "text", "text": text}]
        if tool_call:
            content.append(
                {"type": "toolCall", "id": "tc1", "name": "exec", "arguments": {}}
            )
        turn: dict[str, Any] = {
            "role": "assistant",
            "timestamp": ts,
            "model": "m",
            "stopReason": stop,
            "content": content,
            "usage": usage,
        }
        if rid is not None:
            turn["responseId"] = rid
        return turn

    def _parse(self, turns: list[dict[str, Any]]) -> OpenClawTelemetry:
        return parse_telemetry(
            [{"type": "agent.start", "sessionKey": self.ORCH, "messages": turns}]
        )

    def test_rollup_dropped_and_usage_not_double_counted(self) -> None:
        parse = self._parse(
            [
                self._turn(
                    rid="r1",
                    ts=1000,
                    text="A1",
                    usage={
                        "input": 100,
                        "output": 50,
                        "cacheRead": 800,
                        "totalTokens": 950,
                    },
                ),
                # The roll-up: rid-less, tool-less 'stop' record whose
                # totalTokens is frozen at A1's value while its components sum
                # the block it closes (the shape observed on real captures).
                self._turn(
                    rid=None,
                    ts=1500,
                    text="A1",
                    usage={
                        "input": 105,
                        "output": 220,
                        "cacheRead": 1600,
                        "cacheWrite": 40,
                        "totalTokens": 950,
                    },
                ),
                self._turn(
                    rid="r2",
                    ts=2000,
                    text="A2",
                    usage={"input": 10, "output": 5, "totalTokens": 15},
                ),
            ]
        )
        assert len(parse.orchestrator_turns) == 2
        events = build_events(parse)
        usages = [
            e.output.usage
            for e in events
            if isinstance(e, ModelEvent) and e.output.usage is not None
        ]
        assert len(usages) == 2
        # Without the drop these would be 2400 / 1915.
        assert sum(u.input_tokens_cache_read or 0 for u in usages) == 800
        assert sum(u.total_tokens for u in usages) == 965

    def test_genuine_turns_with_equal_totals_are_kept(self) -> None:
        # On rid-less (service-sink) captures two consecutive genuine text-only
        # replies can repeat a totalTokens value. A genuine per-call record is
        # self-consistent (input + output + cacheRead + cacheWrite ==
        # totalTokens), which a roll-up never is — so the frozen total alone
        # must not delete the second real turn.
        usage = {"input": 10, "output": 40, "cacheRead": 900, "totalTokens": 950}
        parse = self._parse(
            [
                self._turn(rid=None, ts=1000, text="A1", usage=dict(usage)),
                self._turn(rid=None, ts=1500, text="A2", usage=dict(usage)),
            ]
        )
        assert len(parse.orchestrator_turns) == 2

    def test_adjacent_zero_usage_placeholders_are_kept(self) -> None:
        # Adjacent provider-failure placeholders share totalTokens=0 but are
        # self-consistent (0 == 0+0+0+0): both must survive the filter.
        zero = {
            "input": 0,
            "output": 0,
            "cacheRead": 0,
            "cacheWrite": 0,
            "totalTokens": 0,
        }
        parse = self._parse(
            [
                self._turn(
                    rid=None, ts=1000, text="[assistant turn failed]", usage=dict(zero)
                ),
                self._turn(
                    rid=None, ts=1500, text="[assistant turn failed]", usage=dict(zero)
                ),
            ]
        )
        assert len(parse.orchestrator_turns) == 2

    def test_rollup_detected_across_interleaved_surfaces(self) -> None:
        # A turn from another orchestrator surface lands between a block's
        # closing per-call record and its roll-up (multi-surface captures are
        # real). The filter runs per surface, so the interleaving must not
        # mask the frozen-total comparison — and the other surface's genuine
        # turn must survive.
        telegram_turn = {
            "role": "assistant",
            "responseId": "t1",
            "timestamp": 1200,
            "model": "m",
            "stopReason": "stop",
            "content": [{"type": "text", "text": "T1"}],
            "usage": {"input": 5, "output": 10, "cacheRead": 485, "totalTokens": 500},
        }
        parse = parse_telemetry(
            [
                {
                    "type": "agent.start",
                    "sessionKey": self.ORCH,
                    "messages": [
                        self._turn(
                            rid="r1",
                            ts=1000,
                            text="A1",
                            usage={
                                "input": 100,
                                "output": 50,
                                "cacheRead": 800,
                                "totalTokens": 950,
                            },
                        ),
                        self._turn(
                            rid=None,
                            ts=1500,
                            text="A1",
                            usage={
                                "input": 104,
                                "output": 210,
                                "cacheRead": 1650,
                                "cacheWrite": 30,
                                "totalTokens": 950,
                            },
                        ),
                    ],
                },
                {
                    "type": "agent.start",
                    "sessionKey": "agent:main:telegram:chat-1",
                    "messages": [telegram_turn],
                },
            ]
        )
        texts = [content_to_text(t.get("content")) for t in parse.orchestrator_turns]
        assert texts == ["A1", "T1"]

    def test_subagent_schema_a_rollup_dropped(self) -> None:
        # Sub-agent sessions are finalized by the same scaffold, so a
        # roll-up-shaped record inside a session's messages[] must not double
        # the span's usage either.
        sub = "agent:main:subagent:sub-roll"
        per_call = {
            "role": "assistant",
            "responseId": "s1",
            "timestamp": 1000,
            "model": "m",
            "stopReason": "stop",
            "content": [{"type": "text", "text": "S1"}],
            "usage": {"input": 20, "output": 40, "cacheRead": 890, "totalTokens": 950},
        }
        rollup = {
            "role": "assistant",
            "timestamp": 1500,
            "model": "m",
            "stopReason": "stop",
            "content": [{"type": "text", "text": "S1"}],
            "usage": {
                "input": 22,
                "output": 55,
                "cacheRead": 1780,
                "cacheWrite": 10,
                "totalTokens": 950,
            },
        }
        parse = parse_telemetry(
            [
                {
                    "type": "agent.start",
                    "sessionKey": self.ORCH,
                    "messages": [
                        self._turn(
                            rid="r1",
                            ts=500,
                            text="A1",
                            usage={"input": 1, "output": 4, "totalTokens": 5},
                        )
                    ],
                },
                {
                    "type": "agent.start",
                    "sessionKey": sub,
                    "prompt": "do the thing",
                    "messages": [per_call, rollup],
                },
            ]
        )
        assert len(parse.subagents) == 1
        assert len(parse.subagents[0].turns) == 1
        assert parse.subagents[0].n_assistant_turns == 1
        events = build_events(parse)
        sub_usages = [
            e.output.usage
            for e in events
            if isinstance(e, ModelEvent) and e.span_id == sub
        ]
        assert len(sub_usages) == 1
        sub_usage = sub_usages[0]
        assert sub_usage is not None
        assert sub_usage.total_tokens == 950

    def test_moving_total_tokens_is_kept(self) -> None:
        # A rid-less 'stop' record whose totalTokens MOVED is a real turn
        # (service-sink captures have no responseId at all) — never dropped.
        parse = self._parse(
            [
                self._turn(rid=None, ts=1000, text="A1", usage={"totalTokens": 950}),
                self._turn(rid=None, ts=1500, text="A2", usage={"totalTokens": 990}),
            ]
        )
        assert len(parse.orchestrator_turns) == 2

    def test_response_id_or_tool_calls_disqualify(self) -> None:
        # The signature is conjunctive: a responseId, a toolCall, or a
        # non-'stop' stopReason each mark a genuine turn even with frozen
        # totals.
        usage = {"totalTokens": 950}
        parse = self._parse(
            [
                self._turn(rid="r1", ts=1000, text="A1", usage=dict(usage)),
                self._turn(rid="r2", ts=1500, text="A2", usage=dict(usage)),
                self._turn(
                    rid=None,
                    ts=2000,
                    text="A3",
                    usage=dict(usage),
                    tool_call=True,
                    stop="toolUse",
                ),
            ]
        )
        assert len(parse.orchestrator_turns) == 3


class TestMessages:
    def test_assistant_user_and_tool_messages(
        self, raw_events: list[dict[str, Any]]
    ) -> None:
        messages = build_messages(parse_telemetry(raw_events))
        assert messages
        roles = {m.role for m in messages}
        assert roles <= {"user", "assistant", "tool"}

    def test_user_prompts_present(self, raw_events: list[dict[str, Any]]) -> None:
        messages = build_messages(parse_telemetry(raw_events))
        user_texts = [m.text for m in messages if m.role == "user"]
        # The three human Telegram prompts from the fixture.
        assert len(user_texts) == 3
        assert any("echo whoami" in t for t in user_texts)

    def test_conversation_starts_with_user(
        self, raw_events: list[dict[str, Any]]
    ) -> None:
        messages = build_messages(parse_telemetry(raw_events))
        assert messages[0].role == "user"

    def test_tool_messages_match_assistant_tool_calls(
        self, raw_events: list[dict[str, Any]]
    ) -> None:
        messages = build_messages(parse_telemetry(raw_events))
        tool_call_ids = {
            tc.id
            for m in messages
            if isinstance(m, ChatMessageAssistant) and m.tool_calls
            for tc in m.tool_calls
        }
        tool_msg_ids = {
            m.tool_call_id for m in messages if isinstance(m, ChatMessageTool)
        }
        # Every tool message corresponds to an assistant tool call.
        assert tool_msg_ids <= tool_call_ids


class TestOperatorChannel:
    """Inbound operator messages (``message.in``) carry provenance.

    A ``message.in`` whose text matches a user turn marks THAT turn
    ``source="operator"`` (no duplicate message); one with no matching user
    turn (it never entered the session thread, e.g. delivered while the agent
    was busy) becomes its own operator-sourced user message, placed by its
    timestamp.
    """

    def _raw(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "message.in",
                "channel": "telegram",
                "content": "please check the baselines",
                "timestamp": 900,
            },
            {
                "type": "agent.start",
                "sessionKey": "agent:main:main:s1",
                "messages": [
                    {
                        "role": "user",
                        "timestamp": 1000,
                        "idempotencyKey": "m1",
                        "content": "please check the baselines",
                    },
                    {
                        "role": "user",
                        "timestamp": 1500,
                        "content": "[runtime context]",
                    },
                    {
                        "role": "assistant",
                        "responseId": "r1",
                        "timestamp": 2000,
                        "model": "m",
                        "content": [{"type": "text", "text": "on it"}],
                    },
                ],
            },
            # Delivered mid-run but never re-entered the session thread as a
            # user turn: must become its own operator-sourced message.
            {
                "type": "message.in",
                "channel": "telegram",
                "content": "actually, prioritise the ablation",
                "timestamp": 2500,
            },
        ]

    def test_matched_message_in_marks_user_turn_operator(self) -> None:
        messages = build_messages(parse_telemetry(self._raw()))
        by_text = {m.text: m for m in messages if m.role == "user"}
        # The operator-delivered prompt is stamped; no duplicate is added.
        assert by_text["please check the baselines"].source == "operator"
        assert sum(1 for m in messages if m.text == "please check the baselines") == 1
        # A user turn that did not arrive via the operator channel (runtime
        # context) carries no source.
        assert by_text["[runtime context]"].source is None

    def test_unmatched_message_in_becomes_operator_message(self) -> None:
        messages = build_messages(parse_telemetry(self._raw()))
        unmatched = [
            m
            for m in messages
            if m.role == "user" and m.text == "actually, prioritise the ablation"
        ]
        assert len(unmatched) == 1
        assert unmatched[0].source == "operator"
        # Placed by timestamp: after the assistant turn it interrupted.
        roles = [m.role for m in messages]
        assert roles.index("assistant") < messages.index(unmatched[0])

    def test_repeated_operator_send_not_lost(self) -> None:
        # The operator sends the same text twice; only one instance re-entered
        # the thread as a user turn. Occurrence-based reconciliation must
        # surface the second send as its own operator message — set-of-texts
        # semantics silently dropped it once the first occurrence matched.
        raw: list[dict[str, Any]] = [
            {
                "type": "message.in",
                "channel": "telegram",
                "content": "status?",
                "timestamp": 900,
            },
            {
                "type": "agent.start",
                "sessionKey": "agent:main:main:s1",
                "messages": [
                    {"role": "user", "timestamp": 1000, "content": "status?"},
                    {
                        "role": "assistant",
                        "responseId": "r1",
                        "timestamp": 2000,
                        "model": "m",
                        "content": [{"type": "text", "text": "working"}],
                    },
                ],
            },
            {
                "type": "message.in",
                "channel": "telegram",
                "content": "status?",
                "timestamp": 2500,
            },
        ]
        messages = build_messages(parse_telemetry(raw))
        status = [m for m in messages if m.role == "user" and m.text == "status?"]
        assert len(status) == 2
        assert all(m.source == "operator" for m in status)
        # The unmatched second send is placed by its timestamp, after the
        # assistant turn it followed.
        roles = [m.role for m in messages]
        assert roles.index("assistant") < messages.index(status[1])

    def test_twin_text_matches_turn_at_or_after_send(self) -> None:
        # Two user turns share the operator text; the send precedes only the
        # second. A message can only enter the thread at-or-after it arrives,
        # so the LATER twin is stamped and the earlier one left untouched.
        raw: list[dict[str, Any]] = [
            {
                "type": "agent.start",
                "sessionKey": "agent:main:main:s1",
                "messages": [
                    {"role": "user", "timestamp": 500, "content": "ok"},
                    {"role": "user", "timestamp": 1500, "content": "ok"},
                ],
            },
            {
                "type": "message.in",
                "channel": "telegram",
                "content": "ok",
                "timestamp": 1000,
            },
        ]
        messages = build_messages(parse_telemetry(raw))
        users = [m for m in messages if m.role == "user"]
        assert len(users) == 2  # matched: no standalone duplicate added
        assert [m.source for m in users] == [None, "operator"]

    def test_multiline_send_matches_block_content_turn(self) -> None:
        # A multi-line send re-enters the thread as a content-block list; both
        # sides must flatten identically (content_to_text) or the turn is left
        # unstamped AND the send duplicated as a standalone message.
        raw: list[dict[str, Any]] = [
            {
                "type": "message.in",
                "channel": "telegram",
                "content": "line1\nline2",
                "timestamp": 900,
            },
            {
                "type": "agent.start",
                "sessionKey": "agent:main:main:s1",
                "messages": [
                    {
                        "role": "user",
                        "timestamp": 1000,
                        "content": [
                            {"type": "text", "text": "line1"},
                            {"type": "text", "text": "line2"},
                        ],
                    },
                ],
            },
        ]
        messages = build_messages(parse_telemetry(raw))
        users = [m for m in messages if m.role == "user"]
        assert len(users) == 1
        assert users[0].source == "operator"

    def test_unmatched_send_not_in_later_model_input(self) -> None:
        # An unmatched inbound message never entered the session thread — the
        # model never saw it. It belongs in the final message thread, but NOT
        # in later ModelEvents' input (the conversation the model was shown).
        raw: list[dict[str, Any]] = [
            {
                "type": "agent.start",
                "sessionKey": "agent:main:main:s1",
                "messages": [
                    {"role": "user", "timestamp": 1000, "content": "start"},
                    {
                        "role": "assistant",
                        "responseId": "r1",
                        "timestamp": 2000,
                        "model": "m",
                        "content": [{"type": "text", "text": "A1"}],
                    },
                    {
                        "role": "assistant",
                        "responseId": "r2",
                        "timestamp": 3000,
                        "model": "m",
                        "content": [{"type": "text", "text": "A2"}],
                    },
                ],
            },
            {
                "type": "message.in",
                "channel": "telegram",
                "content": "secret aside",
                "timestamp": 2500,
            },
        ]
        events, messages = build_content(parse_telemetry(raw))
        models = [e for e in events if isinstance(e, ModelEvent)]
        assert len(models) == 2
        assert not any(m.text == "secret aside" for m in models[1].input)
        aside = [m for m in messages if m.role == "user" and m.text == "secret aside"]
        assert len(aside) == 1
        assert aside[0].source == "operator"

    def test_fixture_prompts_carry_operator_source(
        self, raw_events: list[dict[str, Any]]
    ) -> None:
        # The bundled fixture's three human Telegram prompts each arrive as a
        # message.in and re-enter the thread as user turns: all three must be
        # stamped, and no extra user message may appear.
        messages = build_messages(parse_telemetry(raw_events))
        users = [m for m in messages if m.role == "user"]
        assert len(users) == 3
        assert all(m.source == "operator" for m in users)


class TestTranscript:
    @pytest.mark.asyncio
    async def test_openclaw_yields_single_transcript(self) -> None:
        transcripts = await _transcripts(FIXTURE)
        assert len(transcripts) == 1

    def test_identity_and_metadata(self) -> None:
        transcript = _single_transcript()
        assert transcript.source_type == OPENCLAW_TELEMETRY_HAL_SOURCE_TYPE
        assert transcript.agent == "openclaw"
        assert transcript.model == "claude-opus-4-8"
        assert transcript.transcript_id
        assert transcript.metadata["n_subagents"] == 3
        # This fixture's orchestrator agent.* events carry the kind-only
        # ``agent:main:main`` key (no id), so there is no session id and the
        # transcript id falls back to the file stem.
        assert transcript.metadata["session_id"] is None
        assert transcript.transcript_id == FIXTURE.stem

    def test_transcript_id_disambiguates_chat_id(self, tmp_path: Path) -> None:
        # The telegram sessionKey's trailing segment is a chat id shared across
        # runs, so it must NOT be the transcript id on its own. source_id carries
        # the bare chat/session id; transcript_id combines it with the run's
        # earliest event timestamp so two runs in the same chat stay distinct.
        from ..transcripts import (
            _create_transcript,
        )

        sk = "agent:main:telegram:default:direct:99999"
        raw = [
            {
                "type": "agent.start",
                "sessionKey": sk,
                "messages": [
                    {
                        "role": "user",
                        "timestamp": 5000,
                        "idempotencyKey": "m1",
                        "content": "hi",
                    },
                    {
                        "role": "assistant",
                        "responseId": "r1",
                        "timestamp": 5100,
                        "model": "m",
                        "content": [{"type": "text", "text": "hello"}],
                    },
                ],
            }
        ]
        transcript = _create_transcript(raw, tmp_path / "telemetry.jsonl")
        assert transcript is not None
        assert transcript.source_id == "99999"  # bare chat/session id
        assert transcript.transcript_id == "99999-5000"  # + earliest event ts
        assert transcript.metadata["session_id"] == "99999"

    def test_totals(self) -> None:
        transcript = _single_transcript()
        assert transcript.message_count == len(transcript.messages)
        assert transcript.total_tokens and transcript.total_tokens > 0
        assert transcript.total_time and transcript.total_time > 0
        assert transcript.date is not None

    def test_total_tokens_is_billable_count_including_cache_reads(self) -> None:
        # The headline total is the billable per-call spend (input + output +
        # cacheRead + cacheWrite) summed over deduped orchestrator + sub-agent
        # turns. Cache reads are billed on every call and must be counted: this
        # fixture's turns carry cache reads, so the headline must strictly exceed
        # the same sum with cache reads removed (guards against dropping them).
        parse = parse_telemetry(read_telemetry_events(FIXTURE))
        turns = [
            *parse.orchestrator_turns,
            *(turn for sa in parse.subagents for turn in sa.turns),
        ]
        expected = sum(tokens_from_usage(t.get("usage")) for t in turns)
        cache_reads = sum(
            int((t.get("usage") or {}).get("cacheRead") or 0) for t in turns
        )
        assert cache_reads > 0  # fixture exercises cache-warm turns

        transcript = _single_transcript()
        assert transcript.total_tokens == expected
        assert transcript.total_tokens > expected - cache_reads

    def test_serializes_round_trip(self) -> None:
        transcript = _single_transcript()
        restored = Transcript.model_validate_json(transcript.model_dump_json())
        assert restored.transcript_id == transcript.transcript_id
        assert restored.message_count == transcript.message_count
        assert len(restored.events) == len(transcript.events)

    @pytest.mark.asyncio
    async def test_empty_file_yields_nothing(self, tmp_path: Path) -> None:
        f = tmp_path / "empty.jsonl"
        f.write_text("")
        assert await _transcripts(f) == []


class TestCrux1SampleExtract:
    """Parsing the ``CRUX1_FIXTURE`` slice (see its definition above).

    Covers the format properties ``FIXTURE`` lacks: the ``seq``/``ts`` envelope,
    ``agent.end`` events, dedup without ``responseId`` (the ``(timestamp,
    content)`` fallback), and a hybrid sub-agent whose work is recorded under
    both schema A and schema B at once.
    """

    @pytest.fixture
    def crux1_raw(self) -> list[dict[str, Any]]:
        return list(read_telemetry_events(CRUX1_FIXTURE))

    def test_seq_ts_envelope_and_agent_end(
        self, crux1_raw: list[dict[str, Any]]
    ) -> None:
        # Service-sink telemetry: every event carries the seq + ts envelope
        # (the raw-dump FIXTURE has neither), plus agent.end events are present.
        assert crux1_raw
        assert all("seq" in e and "ts" in e for e in crux1_raw)
        assert any(e["type"] == "agent.end" for e in crux1_raw)

    def test_dedupes_orchestrator_turns_without_response_id(
        self, crux1_raw: list[dict[str, Any]]
    ) -> None:
        parse = parse_telemetry(crux1_raw)
        # These assistant turns have no responseId, yet the cumulative snapshots
        # still collapse to a deduped set of orchestrator turns. The exact count
        # matters: a dedup regression on the (timestamp, content) fallback path
        # would re-admit duplicated turns and inflate this.
        assert not any(t.get("responseId") for t in parse.orchestrator_turns)
        assert len(parse.orchestrator_turns) == 6

    def test_single_hybrid_subagent_spawn_linked(
        self, crux1_raw: list[dict[str, Any]]
    ) -> None:
        parse = parse_telemetry(crux1_raw)
        assert len(parse.subagents) == 1
        sa = parse.subagents[0]
        # Hybrid: the sub-agent has BOTH schema-A turns and schema-B tool calls.
        assert sa.n_assistant_turns > 0 and sa.n_tool_calls > 0
        assert sa.spawn_tool_call_id is not None

    def test_hybrid_tool_call_not_double_counted(
        self, crux1_raw: list[dict[str, Any]]
    ) -> None:
        parse = parse_telemetry(crux1_raw)
        events = build_events(parse)
        span_ids = {sa.session_key for sa in parse.subagents}
        exec_in_span = [
            e
            for e in events
            if isinstance(e, ToolEvent)
            and e.span_id in span_ids
            and e.function == "exec"
        ]
        # The schema-A turn is authoritative: one exec event, carrying its
        # result -- the duplicate schema-B tool.* event is suppressed.
        assert len(exec_in_span) == 1
        assert exec_in_span[0].result

    def test_subagent_model_events_carry_usage(
        self, crux1_raw: list[dict[str, Any]]
    ) -> None:
        parse = parse_telemetry(crux1_raw)
        events = build_events(parse)
        span_ids = {sa.session_key for sa in parse.subagents}
        sub_models = [
            e for e in events if isinstance(e, ModelEvent) and e.span_id in span_ids
        ]
        # Schema-A sub-agent turns reconstruct ModelEvents with real usage.
        assert sub_models
        assert any(
            e.output.usage and e.output.usage.output_tokens > 0 for e in sub_models
        )

    @pytest.mark.asyncio
    async def test_yields_single_transcript(self) -> None:
        transcripts = await _transcripts(CRUX1_FIXTURE)
        assert len(transcripts) == 1
        assert transcripts[0].metadata["n_subagents"] == 1

    @pytest.mark.asyncio
    async def test_total_tokens_includes_subagent_turns(self) -> None:
        # The hybrid sub-agent carries schema-A turns with their own usage; those
        # tokens must count toward the headline total, so the billable total over
        # orchestrator + sub-agent turns strictly exceeds the orchestrator-only
        # total.
        parse = parse_telemetry(read_telemetry_events(CRUX1_FIXTURE))
        sub_turns = [turn for sa in parse.subagents for turn in sa.turns]
        assert sub_turns  # fixture's sub-agent has schema-A turns with usage
        orch_only = sum(
            tokens_from_usage(t.get("usage")) for t in parse.orchestrator_turns
        )
        expected = orch_only + sum(tokens_from_usage(t.get("usage")) for t in sub_turns)

        transcript = (await _transcripts(CRUX1_FIXTURE))[0]
        assert transcript.total_tokens == expected
        assert transcript.total_tokens > orch_only

    def test_reasoning_preserved_from_thinking_blocks(self) -> None:
        # CRUX1 assistant turns carry ``thinking`` blocks; these must surface as
        # ContentReasoning on the message thread (not be silently dropped as they
        # were before). Guards against a regression to text-only flattening.
        messages = build_messages(parse_telemetry(read_telemetry_events(CRUX1_FIXTURE)))
        reasoning = [
            block
            for m in messages
            if isinstance(m.content, list)
            for block in m.content
            if isinstance(block, ContentReasoning)
        ]
        assert reasoning
        assert all(r.reasoning for r in reasoning)


class TestRichContent:
    """Text, reasoning (``thinking``) and images map to Inspect ``Content``.

    OpenClaw emits ``thinking`` blocks on assistant turns and inline base64
    ``image`` blocks (chiefly screenshot tool results). Both are preserved as
    structured ``Content`` rather than flattened to text; plain-text turns stay
    plain strings.
    """

    def _raw(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "agent.start",
                "sessionKey": "agent:main:main:s1",
                "messages": [
                    {
                        "role": "user",
                        "timestamp": 1,
                        "idempotencyKey": "u1",
                        "content": "take a screenshot",
                    },
                    {
                        "role": "assistant",
                        "responseId": "r1",
                        "timestamp": 2,
                        "model": "claude-x",
                        "content": [
                            {
                                "type": "thinking",
                                "thinking": "I will capture the screen",
                                "thinkingSignature": "SIG",
                            },
                            {"type": "text", "text": "Capturing now"},
                            {
                                "type": "toolCall",
                                "id": "tc1",
                                "name": "screenshot",
                                "arguments": {},
                            },
                        ],
                    },
                    {
                        "role": "toolResult",
                        "toolCallId": "tc1",
                        "timestamp": 3,
                        "content": [
                            {"type": "text", "text": "captured"},
                            {
                                "type": "image",
                                "data": "QUJD",
                                "mimeType": "image/png",
                            },
                        ],
                    },
                ],
            }
        ]

    def test_assistant_thinking_becomes_reasoning(self) -> None:
        messages = build_messages(parse_telemetry(self._raw()))
        assistant = next(m for m in messages if isinstance(m, ChatMessageAssistant))
        assert isinstance(assistant.content, list)
        reasoning = [b for b in assistant.content if isinstance(b, ContentReasoning)]
        text = [b for b in assistant.content if isinstance(b, ContentText)]
        assert [r.reasoning for r in reasoning] == ["I will capture the screen"]
        assert reasoning[0].signature == "SIG"
        assert [t.text for t in text] == ["Capturing now"]
        # The toolCall is surfaced as a tool call, not a content block.
        assert assistant.tool_calls and assistant.tool_calls[0].function == "screenshot"

    def test_tool_result_image_becomes_content_image(self) -> None:
        messages = build_messages(parse_telemetry(self._raw()))
        tool_msg = next(m for m in messages if isinstance(m, ChatMessageTool))
        assert isinstance(tool_msg.content, list)
        images = [b for b in tool_msg.content if isinstance(b, ContentImage)]
        assert len(images) == 1
        # Encoded as a base64 data URI carrying the source mime type.
        assert images[0].image == "data:image/png;base64,QUJD"
        # The accompanying text block is retained alongside the image.
        assert any(
            isinstance(b, ContentText) and b.text == "captured"
            for b in tool_msg.content
        )

    def test_plain_text_turns_stay_strings(self) -> None:
        # The common case (no images/reasoning) must remain a plain string, not a
        # single-element Content list — keeps the vast majority of turns simple.
        messages = build_messages(parse_telemetry(self._raw()))
        user = next(m for m in messages if m.role == "user")
        assert user.content == "take a screenshot"

    def test_image_survives_transcript_round_trip(self, tmp_path: Path) -> None:
        # The base64 image must survive JSON (de)serialization of the transcript.
        from ..transcripts import (
            _create_transcript,
        )

        transcript = _create_transcript(self._raw(), tmp_path / "telemetry.jsonl")
        assert transcript is not None
        restored = Transcript.model_validate_json(transcript.model_dump_json())
        images = [
            b
            for m in restored.messages
            if isinstance(m.content, list)
            for b in m.content
            if isinstance(b, ContentImage)
        ]
        assert images and images[0].image == "data:image/png;base64,QUJD"
