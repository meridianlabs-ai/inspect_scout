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
from inspect_scout.sources._openclaw import (
    OPENCLAW_TELEMETRY_HAL_SOURCE_TYPE,
    openclaw_telemetry_hal,
)
from inspect_scout.sources._openclaw._telemetry_hal.client import (
    discover_telemetry_files,
    read_telemetry_events,
)
from inspect_scout.sources._openclaw._telemetry_hal.events import build_content
from inspect_scout.sources._openclaw._telemetry_hal.extraction import (
    content_to_text,
    tokens_from_usage,
)
from inspect_scout.sources._openclaw._telemetry_hal.parse import (
    OpenClawTelemetry,
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
    from inspect_scout.sources._openclaw._telemetry_hal.transcripts import (
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
        # A kind outside main/telegram/dashboard/subagent on a consumed event
        # means a session whose turns would otherwise be silently discarded
        # (classified as neither orchestrator nor sub-agent), so the import
        # must fail loudly, naming the kind and the sessionKey.
        with pytest.raises(ValueError, match="unrecognized session kind"):
            parse_telemetry([*self._orch_raw("agent:main:main:s1"), event])
        with pytest.raises(ValueError, match=f"kind {expected_kind!r}"):
            parse_telemetry([*self._orch_raw("agent:main:main:s1"), event])

    def test_message_events_without_session_key_are_ignored(self) -> None:
        # message.* events carry no sessionKey and are intentionally not
        # consumed; their missing kind must NOT trip the unrecognized-kind
        # check.
        raw = [
            {"type": "message.in", "channel": "telegram", "content": "hi"},
            *self._orch_raw("agent:main:main:s1"),
            {"type": "message.out", "channel": "telegram", "content": "bye"},
        ]
        assert len(parse_telemetry(raw).orchestrator_turns) == 1

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
        ],
    )
    def test_orchestrator_kinds_yield_orchestrator_turns(
        self, session_key: str
    ) -> None:
        # Every orchestrator surface (terminal, Telegram, web dashboard) must
        # have its assistant turns classified as orchestrator turns; otherwise
        # the transcript is silently dropped for having no turns.
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

    def test_unlinked_subagent_dropped_with_warning(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        # A sub-agent whose spawn cannot be linked to a tool call (no
        # childSessionKey resolvable to a spawn call) cannot be placed in the
        # timeline, so it is dropped with a warning rather than guessed at. Not
        # observed in the CRUX1 captures; this locks the fallback behaviour.
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
        with caplog.at_level(logging.WARNING):
            events = build_events(parse)
        # No span is emitted for the unlinked sub-agent, and it is reported.
        assert not any(isinstance(e, SpanBeginEvent) for e in events)
        assert any(
            "no linkable spawn call" in r.getMessage() and child in r.getMessage()
            for r in caplog.records
        )


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
        from inspect_scout.sources._openclaw._telemetry_hal.transcripts import (
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
        from inspect_scout.sources._openclaw._telemetry_hal.transcripts import (
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
