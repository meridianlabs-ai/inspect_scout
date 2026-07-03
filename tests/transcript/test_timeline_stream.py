"""Tests for the streaming events skeleton (timeline_stream)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, AsyncIterator, Literal

import pytest
from inspect_ai.event import Event, ModelEvent, TimelineEvent, ToolEvent, timeline_build
from inspect_ai.model import ChatMessage, ChatMessageSystem, ContentText
from inspect_scout._transcript.messages import span_messages
from inspect_scout._transcript.timeline import TimelineSpan, _walk_spans
from inspect_scout._transcript.types import Transcript, TranscriptInfo

from tests.transcript.fixtures_agentic import (
    _compaction_event,
    _model_event,
    agentic_events,
    agentic_transcript,
)

try:
    from inspect_ai.event._timeline import (
        _get_system_prompt_for_event,
        _has_tool_calls,
    )
except ImportError:  # pragma: no cover - fallback if private API moves

    def _get_system_prompt_for_event(event: ModelEvent) -> str | None:
        from inspect_ai.model import ChatMessageSystem

        for msg in event.input:
            if isinstance(msg, ChatMessageSystem):
                if isinstance(msg.content, str):
                    return msg.content
                parts = [c.text for c in msg.content if hasattr(c, "text")]
                return "\n".join(parts) if parts else None
        return None

    def _has_tool_calls(event: ModelEvent) -> bool:
        if event.output.choices:
            msg = event.output.choices[0].message
            if msg.tool_calls:
                return True
        return False


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
    from inspect_scout._transcript.timeline import _walk_spans

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


def test_prompt_interning_shares_instances() -> None:
    from inspect_scout._transcript.timeline_stream import _PromptInterner

    interner = _PromptInterner()
    a = interner.intern("p" * 10_000)
    b = interner.intern("p" * 10_000)
    assert a is b


def _span_model_event_uuids(span: TimelineSpan) -> list[str | None]:
    """Return the uuids of ModelEvents directly in `span.content` (not nested)."""
    uuids: list[str | None] = []
    for item in span.content:
        if isinstance(item, TimelineEvent) and isinstance(item.event, ModelEvent):
            uuids.append(item.event.uuid)
    return uuids


def test_stub_tree_matches_full_tree_structure() -> None:
    """The regression guard for Finding 1: stubbing must not change span shape.

    Building the timeline from stubbed events must yield the same
    scannable span names, the same utility classification, and the same
    per-span direct-ModelEvent uuid sequence as building it from the full
    events -- in particular for "handoff_agent", the ToolEvent-with-nested-
    `.events` tool-spawned agent, whose nested ModelEvents would vanish if
    `_stub_tool_event` emptied `.events` instead of recursively stubbing it.
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


def test_stub_preserves_warmup_signal() -> None:
    """Finding 1: stubbing must not destroy the warmup/cache-priming signal.

    ``_wrap_utility_events`` wraps warmup calls (detected by
    ``_is_warmup_call``: ``config.max_tokens <= 1`` plus a single-word
    trailing ``ChatMessageUser`` content) as utility spans. Reducing a
    ``ModelEvent`` stub's ``input`` to system messages only would destroy
    that signal, so a stubbed warmup call would classify differently from
    the materialized one -- inflating ``_is_single_turn`` counts and
    potentially shifting region-last selection.

    ``_is_warmup_call`` is the exact classifier ``timeline_build`` reads, so
    assert directly that the stub preserves its verdict (and the other two
    per-event signals ``_wrap_utility_events`` reads) for a warmup event
    carrying bulk user content, while stripping that bulk.

    (A full ``timeline_build`` over a warmup-containing agent span is not
    exercised here because the upstream ``_wrap_utility_events`` recurses
    into the utility wrapper it creates and re-detects the same warmup call,
    recursing without bound -- a pre-existing ``inspect_ai`` bug that
    crashes the *materialized* build identically to the stub build, so it is
    orthogonal to stub fidelity. The signal-level assertions below are the
    property the stubbing contract must uphold.)
    """
    from inspect_ai.event._timeline import _is_warmup_call
    from inspect_ai.model import ChatMessageUser, GenerateConfig
    from inspect_scout._transcript.timeline_stream import _PromptInterner, stub_event

    # A warmup event built locally: max_tokens=1, single-word trailing user
    # content, but with a leading bulk user turn that must not survive
    # stubbing. `_is_warmup_call` keys on the *last* ChatMessageUser's
    # single-word content, so the trailing "warmup" turn drives detection.
    base = _last_model_event(agentic_events())
    warmup = base.model_copy(
        update={
            "uuid": "evt-warmup-local",
            "input": [
                ChatMessageSystem(content="MAIN"),
                ChatMessageUser(content="bulk conversation " + "w" * 100_000),
                ChatMessageUser(content="warmup"),
            ],
            "config": GenerateConfig(max_tokens=1),
        }
    )
    # Sanity: this really is a warmup call, and it carries strippable bulk.
    assert _is_warmup_call(warmup)

    stub = stub_event(warmup, _PromptInterner())
    assert isinstance(stub, ModelEvent)

    # The three per-event signals `_wrap_utility_events` reads are preserved.
    assert _is_warmup_call(stub) == _is_warmup_call(warmup) is True
    assert _get_system_prompt_for_event(stub) == _get_system_prompt_for_event(warmup)
    assert _has_tool_calls(stub) == _has_tool_calls(warmup)

    # Bulk user content did not survive stubbing.
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
    """Regression: trailing trim (no post-trim ModelEvent) must not over-select uuid-less pre-trim.

    Builds a minimal span ending with:
    ``[ModelEvent(uuid), ModelEvent(uuid=None via model_copy), trim]``

    The pre-trim event (the one with uuid=None) should only be selected if a
    *later* ModelEvent consumes it via _trim_prefix. Since there is no
    post-trim ModelEvent, the uuid-less pre-trim event should NOT be selected.

    Previously, the code eagerly selected the pre-trim event on encountering
    the trim, which would raise _StubSkeletonUnsupported when the pre-trim
    event had no uuid. The fix defers pre-trim selection to the consumption
    point (when a post-trim ModelEvent is encountered), so a trailing trim
    with no post-trim ModelEvent does not try to select the pre-trim uuid.

    This test ensures that:
    1. Selection does not raise _StubSkeletonUnsupported on the uuid-less pre-trim
    2. The uuid-less pre-trim event is not selected (and nothing else is either,
       since the span ends after the trim)
    3. Equivalence still holds for any selected events (vacuously true here)
    """
    from inspect_scout._transcript.timeline_stream import (
        _needed_uuids_for_span,
        _StubSkeletonUnsupported,
    )

    # Build events for a single span: ModelEvent(uuid) -> ModelEvent(no uuid) -> trim
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

    # Selection must not raise _StubSkeletonUnsupported on the uuid-less pre-trim event
    # (it should not try to add it at all, since no ModelEvent follows to consume it).
    try:
        needed = _needed_uuids_for_span(span_events, compaction="all")
    except _StubSkeletonUnsupported:
        pytest.fail(
            "_needed_uuids_for_span raised on trailing trim with uuid-less pre-trim; "
            "should only add pre-trim uuid if later ModelEvent consumes it"
        )

    # After the trim clears current and there's no post-trim ModelEvent,
    # nothing is added. The set should be empty.
    assert needed == set()


def test_selection_is_minimal_all() -> None:
    """Blanking any *selected* ModelEvent must change span_messages output.

    Complements the coverage test: proves selection is not merely a
    superset. Every selected event is load-bearing -- blanking it alone
    perturbs the reconstructed messages of some scannable span.
    """
    from inspect_scout._transcript.timeline_stream import needed_model_event_uuids

    events = agentic_events()
    tree = timeline_build(events)
    needed = needed_model_event_uuids(tree.root, compaction="all", depth=None)
    assert needed  # sanity

    baseline = [
        _dump(span_messages(span, compaction="all"))
        for span in _walk_spans(tree.root, depth=None)
    ]

    all_uuids = _all_model_uuids(events)
    for target in needed:
        # Keep everything except `target`: blanking exactly one selected
        # event must perturb some span's reconstructed messages.
        blanked = _blank_events_except(events, all_uuids - {target})
        blanked_tree = timeline_build(blanked)
        blanked_dump = [
            _dump(span_messages(span, compaction="all"))
            for span in _walk_spans(blanked_tree.root, depth=None)
        ]
        assert blanked_dump != baseline, (
            f"blanking selected event {target!r} did not change output; "
            "selection is not minimal"
        )


def test_selection_includes_first_post_trim_event() -> None:
    """The first ModelEvent after a kept trim compaction is load-bearing.

    Proves both that the fixture's trim compaction now produces a non-empty
    trimmed prefix (the Task-1 review finding), and that selection retains
    the first post-trim ModelEvent whose input ``_trim_prefix`` reads to
    reconstruct that prefix.
    """
    from inspect_scout._transcript.timeline_stream import needed_model_event_uuids

    events = agentic_events()
    tree = timeline_build(events)

    # The fixture's trim actually drops a prefix: compaction="all" surfaces
    # the trimmed marker message.
    main = next(s for s in _walk_spans(tree.root, depth=None) if s.name == "main")
    all_text = [m.text for m in span_messages(main, compaction="all")]
    assert any("trim-dropped-marker" in t for t in all_text)

    needed = needed_model_event_uuids(tree.root, compaction="all", depth=None)
    assert "evt-post-trim" in needed
    assert "evt-pre-trim" in needed

    # Blanking the first post-trim event changes output (the prefix can no
    # longer be reconstructed), confirming its selection is load-bearing.
    blanked = _blank_events_except(events, _all_model_uuids(events) - {"evt-post-trim"})
    blanked_tree = timeline_build(blanked)
    blanked_main = next(
        s for s in _walk_spans(blanked_tree.root, depth=None) if s.name == "main"
    )
    assert _dump(span_messages(main, compaction="all")) != _dump(
        span_messages(blanked_main, compaction="all")
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


def test_stub_model_event_interns_list_content_system_prompt() -> None:
    """Finding 2: list-content ChatMessageSystem parts must be interned too."""
    from inspect_scout._transcript.timeline_stream import _PromptInterner, stub_event

    prompt_text = "list-content-system-prompt " + "q" * 10_000
    base = agentic_events()[2]
    assert isinstance(base, ModelEvent)
    assert base.uuid is not None
    base_uuid = base.uuid

    def _with_list_system_prompt(label_suffix: str) -> ModelEvent:
        list_content_message = ChatMessageSystem(
            content=[ContentText(text=prompt_text)]
        )
        other_input = [m for m in base.input if not isinstance(m, ChatMessageSystem)]
        return base.model_copy(
            update={
                "uuid": base_uuid + label_suffix,
                "input": [list_content_message, *other_input],
            }
        )

    event_a = _with_list_system_prompt("-a")
    event_b = _with_list_system_prompt("-b")

    interner = _PromptInterner()
    stub_a = stub_event(event_a, interner)
    stub_b = stub_event(event_b, interner)
    assert isinstance(stub_a, ModelEvent)
    assert isinstance(stub_b, ModelEvent)

    # The system-prompt signal the classifier reads is preserved.
    assert _get_system_prompt_for_event(stub_a) == _get_system_prompt_for_event(event_a)
    assert _get_system_prompt_for_event(stub_b) == _get_system_prompt_for_event(event_b)

    # Interning applies to list-content parts: two events with identical
    # list-content prompts share the interned part text instance.
    stub_sys_a = stub_a.input[0]
    stub_sys_b = stub_b.input[0]
    assert isinstance(stub_sys_a, ChatMessageSystem)
    assert isinstance(stub_sys_b, ChatMessageSystem)
    assert isinstance(stub_sys_a.content, list)
    assert isinstance(stub_sys_b.content, list)
    part_a = stub_sys_a.content[0]
    part_b = stub_sys_b.content[0]
    assert isinstance(part_a, ContentText)
    assert isinstance(part_b, ContentText)
    assert part_a.text is part_b.text


def _info(transcript: Transcript) -> TranscriptInfo:
    return TranscriptInfo(transcript_id=transcript.transcript_id)


@pytest.mark.asyncio
@pytest.mark.parametrize("compaction", ["all", "last", 2])
@pytest.mark.parametrize("depth", [None, 1])
async def test_stream_equals_materialized_segments(
    compaction: Literal["all", "last"] | int, depth: int | None
) -> None:
    from inspect_scout._scanner.extract import message_numbering
    from inspect_scout._transcript.handle import MaterializedTranscriptHandle
    from inspect_scout._transcript.timeline import timeline_messages
    from inspect_scout._transcript.timeline_stream import stream_timeline_messages

    transcript = agentic_transcript()

    async def load() -> Transcript:
        return transcript

    handle = MaterializedTranscriptHandle(load, _info(transcript))

    def numbering() -> Any:  # fresh numbering scope per path
        return message_numbering()[0]

    streamed = [
        (seg.span.id, seg.messages_str)
        async for seg in stream_timeline_messages(
            handle,
            messages_as_str=numbering(),
            model="mockllm/model",
            compaction=compaction,
            depth=depth,
        )
    ]
    materialized = [
        (seg.span.id, seg.messages_str)
        async for seg in timeline_messages(
            timeline_build(transcript.events).root,
            messages_as_str=numbering(),
            model="mockllm/model",
            compaction=compaction,
            depth=depth,
        )
    ]
    assert streamed == materialized


LOGS_DIR = Path(__file__).parent.parent / "recorder" / "logs"
LOGS = sorted(LOGS_DIR.glob("*.eval"))


@pytest.mark.asyncio
@pytest.mark.parametrize("log", LOGS, ids=[log.name for log in LOGS])
async def test_stream_equals_materialized_segments_eval_logs(
    log: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Fidelity over real `.eval` fixtures, forced through the spooled path."""
    from inspect_scout._scanner.extract import message_numbering
    from inspect_scout._transcript.eval_log import EvalLogTranscriptsView
    from inspect_scout._transcript.handle import SpooledTranscriptHandle
    from inspect_scout._transcript.timeline import timeline_build, timeline_messages
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
            streamed = [
                (seg.span.id, seg.messages_str)
                async for seg in stream_timeline_messages(
                    handle,
                    messages_as_str=numbering(),
                    model="mockllm/model",
                    compaction="all",
                    depth=None,
                )
            ]
        materialized_segments = [
            (seg.span.id, seg.messages_str)
            async for seg in timeline_messages(
                timeline_build(materialized.events).root,
                messages_as_str=numbering(),
                model="mockllm/model",
                compaction="all",
                depth=None,
            )
        ]
        assert streamed  # non-vacuous: the fixture must yield >=1 segment
        assert streamed == materialized_segments
    finally:
        await view.disconnect()


class _FlakyHandle:
    """Test double violating the `TranscriptHandle` multi-shot contract.

    `events()` returns the full event list (including a needed `ModelEvent`)
    on its first call, but omits that same event on the second call. Pass 1
    of `stream_timeline_messages` selects the event's uuid from the first
    stream; pass 2 must fail to find a full event for it on the second
    stream, which should surface as `_StubSkeletonUnsupported` rather than
    silently substituting a stub or crashing.
    """

    def __init__(self, events: list[Event], *, omit_uuid: str) -> None:
        self._events = events
        self._omit_uuid = omit_uuid
        self._call_count = 0

    async def events(self, *, types: object = None) -> AsyncIterator[Event]:
        self._call_count += 1
        first_call = self._call_count == 1
        for event in self._events:
            if not first_call and getattr(event, "uuid", None) == self._omit_uuid:
                continue
            yield event


@pytest.mark.asyncio
async def test_stream_raises_on_multi_shot_violation() -> None:
    """Pass 2 must raise `_StubSkeletonUnsupported` if `events()` is flaky.

    Regression guard for the multi-shot contract check in
    `stream_timeline_messages`: if a handle's second `events()` call omits
    a `ModelEvent` that pass 1 selected from the first call, pass 2 cannot
    find a full event for that uuid and must raise rather than silently
    dropping content.
    """
    from inspect_scout._scanner.extract import message_numbering
    from inspect_scout._transcript.timeline_stream import (
        _StubSkeletonUnsupported,
        stream_timeline_messages,
    )

    events = agentic_events()
    omit_uuid = _last_model_event(events).uuid
    assert omit_uuid is not None
    handle = _FlakyHandle(events, omit_uuid=omit_uuid)

    with pytest.raises(_StubSkeletonUnsupported):
        [
            seg
            async for seg in stream_timeline_messages(
                handle,  # type: ignore[arg-type]
                messages_as_str=message_numbering()[0],
                model="mockllm/model",
                compaction="last",
                depth=None,
            )
        ]
