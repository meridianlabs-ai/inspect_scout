"""Tests for the streaming events skeleton (timeline_stream)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, AsyncIterator, Literal

import pytest
from inspect_ai.event import Event, ModelEvent, TimelineEvent, ToolEvent, timeline_build
from inspect_ai.event._timeline import (
    _get_system_prompt_for_event,
    _has_tool_calls,
)
from inspect_ai.model import ChatMessage, ChatMessageSystem, ContentText
from inspect_scout._transcript.messages import span_messages
from inspect_scout._transcript.timeline import TimelineSpan, _walk_spans
from inspect_scout._transcript.types import Transcript, TranscriptInfo

from tests.transcript.fixtures_agentic import (
    _compaction_event,
    _model_event,
    agentic_events,
    agentic_transcript,
    reset_ids,
)


@pytest.fixture(autouse=True)
def _reset_fixture_ids() -> None:
    """Tests here build events via `_model_event`/`_compaction_event` directly.

    Those builders share a module-level timestamp counter with
    `agentic_events()`, so reset it per test for deterministic events.
    """
    reset_ids()


def _collect_utility(span: TimelineSpan) -> list[TimelineSpan]:
    """Recursively collect every utility-classified span in the tree."""
    utility: list[TimelineSpan] = []
    if span.utility:
        utility.append(span)
    for item in span.content:
        if isinstance(item, TimelineSpan):
            utility.extend(_collect_utility(item))
    return utility


def test_agentic_fixture_classification() -> None:
    """The fixture must exercise the classification paths the spec names."""
    tree = timeline_build(agentic_events())
    spans = list(_walk_spans(tree.root, depth=None))
    names = [s.name for s in spans]
    # main agent, sub2 (non-utility nested agent), the span-based tool-spawned
    # agent ("browser"), and the flat-ToolEvent tool-spawned agent
    # ("handoff_agent") are scannable; "sub" (utility) and the wrapped helper
    # are NOT.
    assert "main" in names
    assert "sub2" in names
    assert "browser" in names
    assert "handoff_agent" in names
    assert "sub" not in names
    utility_spans = _collect_utility(tree.root)
    assert len(utility_spans) >= 2  # "sub" + wrapped foreign-prompt helper

    # Non-vacuity: the fixture's trim compaction really drops a prefix, so
    # trim-selection paths are exercised — compaction="all" surfaces the
    # trimmed marker message in "main"'s reconstructed messages.
    main = next(s for s in spans if s.name == "main")
    all_text = [m.text for m in span_messages(main, compaction="all")]
    assert any("trim-dropped-marker" in t for t in all_text)


def test_stub_model_event_preserves_classification_signals() -> None:
    from inspect_scout._transcript.timeline_stream import _PromptInterner, stub_event

    events = agentic_events(big_payload="y" * 100_000)
    interner = _PromptInterner()
    for ev in events:
        stub = stub_event(ev, interner)
        assert stub.uuid == ev.uuid and stub.span_id == ev.span_id
        if isinstance(ev, ModelEvent):
            assert isinstance(stub, ModelEvent)
            assert _get_system_prompt_for_event(stub) == _get_system_prompt_for_event(
                ev
            )
            assert _has_tool_calls(stub) == _has_tool_calls(ev)
            assert "y" * 1000 not in stub.model_dump_json()
        if isinstance(ev, ToolEvent):
            assert isinstance(stub, ToolEvent)
            assert stub.agent == ev.agent and stub.function == ev.function
            assert "y" * 1000 not in stub.model_dump_json()


def _span_model_event_uuids(span: TimelineSpan) -> list[str | None]:
    """Return the uuids of ModelEvents directly in `span.content` (not nested)."""
    uuids: list[str | None] = []
    for item in span.content:
        if isinstance(item, TimelineEvent) and isinstance(item.event, ModelEvent):
            uuids.append(item.event.uuid)
    return uuids


def test_stub_tree_matches_full_tree_structure() -> None:
    """Stubbing must not change span shape.

    Building the timeline from stubbed events yields the same scannable span
    names, utility classification, and per-span direct-ModelEvent uuid
    sequence as building it from the full events -- including
    "handoff_agent", the ToolEvent-with-nested-`.events` tool-spawned agent,
    whose nested ModelEvents would vanish if `_stub_tool_event` emptied
    `.events` instead of recursively stubbing it.
    """
    from inspect_scout._transcript.timeline_stream import _PromptInterner, stub_event

    events = agentic_events(big_payload="z" * 100_000)
    interner = _PromptInterner()
    stubbed_events: list[Event] = [stub_event(e, interner) for e in events]

    full_tree = timeline_build(events)
    stub_tree = timeline_build(stubbed_events)

    full_spans = list(_walk_spans(full_tree.root, depth=None))
    stub_spans = list(_walk_spans(stub_tree.root, depth=None))

    full_names = [s.name for s in full_spans]
    stub_names = [s.name for s in stub_spans]
    assert stub_names == full_names
    assert "handoff_agent" in full_names

    full_utility = _collect_utility(full_tree.root)
    stub_utility = _collect_utility(stub_tree.root)
    assert [s.name for s in stub_utility] == [s.name for s in full_utility]

    for full_span, stub_span in zip(full_spans, stub_spans, strict=True):
        assert full_span.utility == stub_span.utility
        assert _span_model_event_uuids(stub_span) == _span_model_event_uuids(full_span)

    # The nested ModelEvents inside handoff-tool's `.events` must survive
    # stubbing with distinct uuids and bulk content stripped.
    handoff_span = next(s for s in stub_spans if s.name == "handoff_agent")
    nested_uuids = _span_model_event_uuids(handoff_span)
    assert nested_uuids == ["evt-handoff-1", "evt-handoff-2"]
    assert "z" * 1000 not in handoff_span.model_dump_json()


@pytest.mark.parametrize(
    ("trailing_user_content", "expected_warmup"),
    [
        pytest.param("warmup", True, id="warmup"),
        pytest.param("Is the answer correct? Reply yes or no.", False, id="judge"),
    ],
)
def test_stub_preserves_warmup_signal(
    trailing_user_content: str, expected_warmup: bool
) -> None:
    """Stubbing a max_tokens=1 ``ModelEvent`` must preserve its warmup verdict.

    ``_is_warmup_call``'s verdict (True for a single-word trailing user turn,
    False for a multi-word judge/classifier call) and the other per-event
    signals ``_wrap_utility_events`` reads must survive stubbing, while bulk
    user content is still stripped.

    (A full ``timeline_build`` over a warmup span is not exercised here: it
    hits an upstream ``inspect_ai`` unbounded-recursion bug identically on
    both the stub and materialized paths, so this asserts at the classifier
    boundary instead.)
    """
    from inspect_ai.event._timeline import _is_warmup_call
    from inspect_ai.model import ChatMessageUser, GenerateConfig
    from inspect_scout._transcript.timeline_stream import _PromptInterner, stub_event

    base = _last_model_event(agentic_events())
    event = base.model_copy(
        update={
            "uuid": "evt-warmup-local",
            "input": [
                ChatMessageSystem(content="MAIN"),
                ChatMessageUser(content="bulk conversation " + "w" * 100_000),
                ChatMessageUser(content=trailing_user_content),
            ],
            "config": GenerateConfig(max_tokens=1),
        }
    )
    # Sanity: the classifier's pre-stub verdict matches the expectation.
    assert _is_warmup_call(event) is expected_warmup

    stub = stub_event(event, _PromptInterner())
    assert isinstance(stub, ModelEvent)

    # The three per-event signals `_wrap_utility_events` reads are preserved.
    assert _is_warmup_call(stub) is expected_warmup
    assert _get_system_prompt_for_event(stub) == _get_system_prompt_for_event(event)
    assert _has_tool_calls(stub) == _has_tool_calls(event)
    # Bulk stripped: the 100KB user turn must not survive stubbing.
    assert "w" * 1000 not in stub.model_dump_json()


def _blank_model_event(event: ModelEvent) -> ModelEvent:
    """Blank the content ``span_messages`` reads, preserving classification.

    Reuses ``stub_event`` (with a private, per-call interner): the stub
    reduces ``input`` to system messages only and empties the output
    message's content while keeping ``tool_calls`` truthiness and the
    system prompt -- exactly the classification signals ``timeline_build``
    reads. That makes it the right blanking operator for the selection
    property test: an event whose content ``span_messages`` never touches
    can be blanked with zero effect on the reconstructed messages, while
    an event whose content *is* touched changes the output the moment it
    is blanked.
    """
    from inspect_scout._transcript.timeline_stream import _PromptInterner, stub_event

    blanked = stub_event(event, _PromptInterner())
    assert isinstance(blanked, ModelEvent)
    return blanked


def _blank_events_except(events: list[Event], keep: set[str]) -> list[Event]:
    """Return ``events`` with every ModelEvent whose uuid is NOT in ``keep`` blanked.

    Recurses into ``ToolEvent.events`` so nested tool-spawned-agent
    ModelEvents (e.g. those inside the ``handoff-tool``) are blanked too;
    they are not present at the top level of the flat event list.
    """
    out: list[Event] = []
    for event in events:
        if isinstance(event, ModelEvent):
            out.append(event if event.uuid in keep else _blank_model_event(event))
        elif isinstance(event, ToolEvent) and event.events:
            out.append(
                event.model_copy(
                    update={"events": _blank_events_except(event.events, keep)}
                )
            )
        else:
            out.append(event)
    return out


def _all_model_uuids(events: list[Event]) -> set[str]:
    """Collect every ModelEvent uuid, recursing into ``ToolEvent.events``."""
    uuids: set[str] = set()
    for event in events:
        if isinstance(event, ModelEvent) and event.uuid is not None:
            uuids.add(event.uuid)
        elif isinstance(event, ToolEvent) and event.events:
            uuids |= _all_model_uuids(event.events)
    return uuids


def _dump(msgs: list[ChatMessage]) -> list[dict[str, Any]]:
    return [m.model_dump() for m in msgs]


def _last_model_event(events: list[Event]) -> ModelEvent:
    for event in reversed(events):
        if isinstance(event, ModelEvent):
            return event
    raise AssertionError("fixture contains no ModelEvent")


@pytest.mark.parametrize("compaction", ["all", "last", 2])
def test_selection_covers_span_messages_reads(
    compaction: Literal["all", "last"] | int,
) -> None:
    """Every ModelEvent whose data span_messages uses is selected.

    Property: blanking every *non-selected* ModelEvent's content must leave
    ``span_messages`` output over every scannable span byte-for-byte
    unchanged. If selection missed an event whose content span_messages
    reads, blanking it would perturb the output and this assertion fails.
    """
    from inspect_scout._transcript.timeline_stream import needed_model_event_uuids

    events = agentic_events()
    tree = timeline_build(events)
    needed = needed_model_event_uuids(tree.root, compaction=compaction, depth=None)

    blanked = _blank_events_except(events, needed)
    blanked_tree = timeline_build(blanked)
    for span, blanked_span in zip(
        _walk_spans(tree.root, depth=None),
        _walk_spans(blanked_tree.root, depth=None),
        strict=True,
    ):
        assert _dump(span_messages(span, compaction=compaction)) == _dump(
            span_messages(blanked_span, compaction=compaction)
        )


def test_trim_at_span_end_does_not_over_select() -> None:
    """A trailing trim with no post-trim ModelEvent must not select the pre-trim event.

    The pre-trim event is uuid-less; selection must not try to add it, and
    must not raise ``_StubSkeletonUnsupported`` while deciding that.
    """
    from inspect_scout._transcript.timeline_stream import _needed_uuids_for_span

    # A single span: ModelEvent(uuid) -> ModelEvent(no uuid) -> trim.
    model_1 = _model_event(
        label="trim-pre-1",
        system_prompt="TEST",
        output_text="before trim",
        span_id=None,
    )
    model_2_no_uuid = _model_event(
        label="trim-pre-2-no-uuid",
        system_prompt="TEST",
        output_text="trimmed away",
        span_id=None,
    ).model_copy(update={"uuid": None})
    trim_event = _compaction_event(label="trim", type="trim", span_id=None)

    span_events: list[Event] = [model_1, model_2_no_uuid, trim_event]

    # No ModelEvent follows to consume the pre-trim event, so selection must
    # not try to add it (and must not raise doing so).
    needed = _needed_uuids_for_span(span_events, compaction="all")

    assert needed == set()


@pytest.mark.parametrize("compaction", ["all", "last", 2])
def test_selection_is_minimal(compaction: Literal["all", "last"] | int) -> None:
    """Blanking any *selected* ModelEvent must change span_messages output.

    Complements the coverage test: proves selection is not merely a
    superset. Every selected event is load-bearing -- blanking it alone
    perturbs the reconstructed messages of some scannable span. This is the
    memory guard; the under-selection direction is pinned by
    ``test_selection_covers_span_messages_reads``.
    """
    from inspect_scout._transcript.timeline_stream import needed_model_event_uuids

    events = agentic_events()
    tree = timeline_build(events)
    needed = needed_model_event_uuids(tree.root, compaction=compaction, depth=None)
    assert needed  # sanity

    baseline = [
        _dump(span_messages(span, compaction=compaction))
        for span in _walk_spans(tree.root, depth=None)
    ]

    all_uuids = _all_model_uuids(events)
    for target in needed:
        # Keep everything except `target`: blanking exactly one selected
        # event must perturb some span's reconstructed messages.
        blanked = _blank_events_except(events, all_uuids - {target})
        blanked_tree = timeline_build(blanked)
        blanked_dump = [
            _dump(span_messages(span, compaction=compaction))
            for span in _walk_spans(blanked_tree.root, depth=None)
        ]
        assert blanked_dump != baseline, (
            f"blanking selected event {target!r} did not change output; "
            "selection is not minimal"
        )


def test_selection_uuidless_raises() -> None:
    from inspect_scout._transcript.timeline_stream import (
        _StubSkeletonUnsupported,
        needed_model_event_uuids,
    )

    events = agentic_events()
    target = _last_model_event(events)
    events = [e.model_copy(update={"uuid": None}) if e is target else e for e in events]
    tree = timeline_build(events)
    with pytest.raises(_StubSkeletonUnsupported):
        needed_model_event_uuids(tree.root, compaction="last", depth=None)


@pytest.mark.parametrize("content_kind", ["str", "list"])
def test_stub_model_event_interns_system_prompt(
    content_kind: Literal["str", "list"],
) -> None:
    """Equal system prompts across stubbed events share one interned instance.

    Covers both string-content and list-content ``ChatMessageSystem``
    prompts. The two events' prompt strings are deliberately built as
    distinct-but-equal objects so the identity assertion can only pass via
    interning (a shared input str would make it pass vacuously).
    """
    from inspect_scout._transcript.timeline_stream import _PromptInterner, stub_event

    base = agentic_events()[2]
    assert isinstance(base, ModelEvent)
    assert base.uuid is not None
    base_uuid = base.uuid

    def _with_system_prompt(label_suffix: str) -> ModelEvent:
        # Fresh, distinct-but-equal prompt string per event.
        prompt_text = "".join(["system ", "prompt ", "text "]) * 50
        system_message = (
            ChatMessageSystem(content=prompt_text)
            if content_kind == "str"
            else ChatMessageSystem(content=[ContentText(text=prompt_text)])
        )
        other_input = [m for m in base.input if not isinstance(m, ChatMessageSystem)]
        return base.model_copy(
            update={
                "uuid": base_uuid + label_suffix,
                "input": [system_message, *other_input],
            }
        )

    event_a = _with_system_prompt("-a")
    event_b = _with_system_prompt("-b")

    def _prompt_obj(event: ModelEvent) -> str:
        system = event.input[0]
        assert isinstance(system, ChatMessageSystem)
        if isinstance(system.content, str):
            return system.content
        part = system.content[0]
        assert isinstance(part, ContentText)
        return part.text

    # Sanity: equal but NOT identical inputs — otherwise the `is` assertions
    # below would pass even with interning disabled.
    assert _prompt_obj(event_a) == _prompt_obj(event_b)
    assert _prompt_obj(event_a) is not _prompt_obj(event_b)

    interner = _PromptInterner()
    stub_a = stub_event(event_a, interner)
    stub_b = stub_event(event_b, interner)
    assert isinstance(stub_a, ModelEvent)
    assert isinstance(stub_b, ModelEvent)

    # The system-prompt signal the classifier reads is preserved.
    assert _get_system_prompt_for_event(stub_a) == _get_system_prompt_for_event(event_a)
    assert _get_system_prompt_for_event(stub_b) == _get_system_prompt_for_event(event_b)

    # Interning: the two stubs' system-prompt content is the SAME object.
    stub_sys_a = stub_a.input[0]
    stub_sys_b = stub_b.input[0]
    assert isinstance(stub_sys_a, ChatMessageSystem)
    assert isinstance(stub_sys_b, ChatMessageSystem)
    if content_kind == "str":
        assert isinstance(stub_sys_a.content, str)
        assert isinstance(stub_sys_b.content, str)
        assert stub_sys_a.content is stub_sys_b.content
    else:
        assert isinstance(stub_sys_a.content, list)
        assert isinstance(stub_sys_b.content, list)
        part_a = stub_sys_a.content[0]
        part_b = stub_sys_b.content[0]
        assert isinstance(part_a, ContentText)
        assert isinstance(part_b, ContentText)
        assert part_a.text is part_b.text


def _info(transcript: Transcript) -> TranscriptInfo:
    return TranscriptInfo(transcript_id=transcript.transcript_id)


def _scrub_agent_result(obj: Any) -> Any:
    """Recursively null out `agent_result` fields in a `model_dump()` tree.

    Isolates the one accepted fidelity loss (see `timeline_stream`'s module
    docstring) so span-tree equality checks can pin "no other divergence".
    """
    if isinstance(obj, dict):
        return {
            key: None if key == "agent_result" else _scrub_agent_result(value)
            for key, value in obj.items()
        }
    if isinstance(obj, list):
        return [_scrub_agent_result(item) for item in obj]
    return obj


@pytest.mark.asyncio
@pytest.mark.parametrize("compaction", ["all", "last", 2])
@pytest.mark.parametrize("depth", [None, 1])
async def test_stream_equals_materialized_segments(
    compaction: Literal["all", "last"] | int, depth: int | None
) -> None:
    """Streamed and materialized extraction agree on messages and span structure.

    Two assertions for two properties. The `messages_str` equality is the
    content guard: it is what fails if an unsubstituted stub ever reaches
    rendered output. The span-dump equality is the structure guard. They are
    not redundant -- dropping one pass-2 substitution fails the first and
    leaves the second green, because `TimelineEvent` serializes its event as
    a bare uuid.
    """
    from inspect_scout._scanner.extract import message_numbering
    from inspect_scout._transcript.handle import MaterializedTranscriptHandle
    from inspect_scout._transcript.messages import transcript_messages
    from inspect_scout._transcript.timeline import TimelineMessages
    from inspect_scout._transcript.timeline_stream import stream_timeline_messages

    transcript = agentic_transcript()

    async def load() -> Transcript:
        return transcript

    handle = MaterializedTranscriptHandle(load, _info(transcript))

    def numbering() -> Any:  # fresh numbering scope per path
        return message_numbering()[0]

    streamed_segments = [
        seg
        async for seg in stream_timeline_messages(
            handle,
            messages_as_str=numbering(),
            model="mockllm/model",
            compaction=compaction,
            depth=depth,
        )
    ]
    materialized_segments: list[TimelineMessages] = []
    async for seg in transcript_messages(
        transcript,
        messages_as_str=numbering(),
        model="mockllm/model",
        compaction=compaction,
        depth=depth,
    ):
        assert isinstance(seg, TimelineMessages)
        materialized_segments.append(seg)
    streamed = [(seg.span.id, seg.messages_str) for seg in streamed_segments]
    materialized = [(seg.span.id, seg.messages_str) for seg in materialized_segments]
    assert streamed == materialized

    # Span structure, not payloads: `TimelineEvent` serializes its event as a
    # bare uuid, so this pins per-span event identity and ordering. Payload
    # divergence is caught by the `messages_str` equality above. `agent_result`
    # is a span field, hence the scrub (see timeline_stream's module docstring).
    for s_seg, m_seg in zip(streamed_segments, materialized_segments, strict=True):
        assert _scrub_agent_result(s_seg.span.model_dump()) == _scrub_agent_result(
            m_seg.span.model_dump()
        )


LOGS_DIR = Path(__file__).parent.parent / "recorder" / "logs"
LOGS = sorted(LOGS_DIR.glob("*.eval"))
assert LOGS, f"no .eval fixtures found in {LOGS_DIR}"


@pytest.mark.asyncio
@pytest.mark.parametrize("log", LOGS, ids=[log.name for log in LOGS])
async def test_stream_equals_materialized_segments_eval_logs(
    log: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Fidelity over real `.eval` fixtures, forced through the spooled path."""
    from inspect_scout._scanner.extract import message_numbering
    from inspect_scout._transcript.eval_log import EvalLogTranscriptsView
    from inspect_scout._transcript.handle import SpooledTranscriptHandle
    from inspect_scout._transcript.messages import transcript_messages
    from inspect_scout._transcript.timeline import TimelineMessages
    from inspect_scout._transcript.timeline_stream import stream_timeline_messages
    from inspect_scout._transcript.types import TranscriptContent
    from inspect_scout._util import constants as constants_mod

    monkeypatch.setattr(constants_mod, "SPOOL_THRESHOLD_BYTES", 0)
    content = TranscriptContent(events="all")

    view = EvalLogTranscriptsView(str(log))
    await view.connect()
    try:
        infos = [i async for i in view.select()]
        assert infos
        info = infos[0]
        materialized = await view.read(info, content)

        def numbering() -> Any:  # fresh numbering scope per path
            return message_numbering()[0]

        async with await view.open(info, content) as handle:
            assert isinstance(handle, SpooledTranscriptHandle)
            streamed_segments = [
                seg
                async for seg in stream_timeline_messages(
                    handle,
                    messages_as_str=numbering(),
                    model="mockllm/model",
                    compaction="all",
                    depth=None,
                )
            ]
        materialized_segments: list[TimelineMessages] = []
        async for seg in transcript_messages(
            materialized,
            messages_as_str=numbering(),
            model="mockllm/model",
            compaction="all",
            depth=None,
        ):
            assert isinstance(seg, TimelineMessages)
            materialized_segments.append(seg)
        streamed = [(seg.span.id, seg.messages_str) for seg in streamed_segments]
        materialized_tuples = [
            (seg.span.id, seg.messages_str) for seg in materialized_segments
        ]
        assert streamed  # non-vacuous: the fixture must yield >=1 segment
        assert streamed == materialized_tuples

        # Span structure, not payloads -- see the in-memory equivalence test
        # above for why this and the `messages_str` equality are both needed.
        for s_seg, m_seg in zip(streamed_segments, materialized_segments, strict=True):
            assert _scrub_agent_result(s_seg.span.model_dump()) == _scrub_agent_result(
                m_seg.span.model_dump()
            )
    finally:
        await view.disconnect()


class _FlakyHandle:
    """Test double violating the `TranscriptHandle` multi-shot contract.

    `events()` returns the full event list (including a needed `ModelEvent`)
    on its first call, but omits that same event on the second call. Pass 1
    of `stream_timeline_messages` selects the event's uuid from the first
    stream; pass 2 must fail to find a full event for it on the second
    stream, and must say so rather than silently substituting a stub.
    """

    def __init__(self, events: list[Event], *, omit_uuid: str) -> None:
        self._events = events
        self._omit_uuid = omit_uuid
        self._call_count = 0

    @property
    def info(self) -> TranscriptInfo:
        return TranscriptInfo(transcript_id="flaky")

    async def events(self) -> AsyncIterator[Event]:
        self._call_count += 1
        first_call = self._call_count == 1
        for event in self._events:
            if not first_call and getattr(event, "uuid", None) == self._omit_uuid:
                continue
            yield event

    def messages(self) -> AsyncIterator[ChatMessage]:
        raise AssertionError("_FlakyHandle exercises the events() path only")

    async def load(self) -> Transcript:
        raise AssertionError("_FlakyHandle exercises the events() path only")

    async def __aenter__(self) -> _FlakyHandle:
        return self

    async def __aexit__(self, *exc: object) -> None:
        return None

    async def aclose(self) -> None:
        return None


@pytest.mark.asyncio
async def test_stream_raises_on_multi_shot_violation() -> None:
    """A handle whose second `events()` call omits a pass-1-selected event must raise.

    The error must not be `_StubSkeletonUnsupported`: `llm_scanner` treats that
    as "fall back to a materialized scan", which would hand the same untrusted
    handle a second chance instead of surfacing the broken contract.
    """
    from inspect_scout._scanner.extract import message_numbering
    from inspect_scout._transcript.timeline_stream import stream_timeline_messages

    events = agentic_events()
    omit_uuid = _last_model_event(events).uuid
    assert omit_uuid is not None
    handle = _FlakyHandle(events, omit_uuid=omit_uuid)

    # Not _StubSkeletonUnsupported, which is not a RuntimeError.
    with pytest.raises(RuntimeError, match="multi-shot contract"):
        [
            seg
            async for seg in stream_timeline_messages(
                handle,
                messages_as_str=message_numbering()[0],
                model="mockllm/model",
                compaction="last",
                depth=None,
            )
        ]
