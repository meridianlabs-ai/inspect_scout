"""End-to-end scan through the streaming (spooled handle) seam.

Forces every eval-log transcript through ``SpooledTranscriptHandle`` by
monkeypatching the streaming byte threshold to 0, runs a real ``scan()`` with
handle-capable ``llm_scanner`` scanners, and asserts both that results are
recorded correctly and that the streaming path was actually taken -- each
shared spooled handle is created and closed exactly once per transcript by
the real ``on_complete`` counter in ``_scan.py``.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import anyio
import pytest
from inspect_ai.model import ModelOutput
from inspect_scout import Scanner, llm_scanner, scan, scanner
from inspect_scout._scanresults import scan_results_df
from inspect_scout._transcript import handle as handle_mod
from inspect_scout._transcript.database.parquet import ParquetTranscriptsDB
from inspect_scout._transcript.factory import transcripts_from
from inspect_scout._transcript.types import Transcript, TranscriptContent

from tests.transcript.fixtures_agentic import agentic_transcript

LOGS_DIR = Path(__file__).parent.parent.parent / "examples" / "scanner" / "logs"


def _spy_spooled_handles(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[list[handle_mod.SpooledTranscriptHandle], dict[int, int]]:
    """Spy on SpooledTranscriptHandle create/close.

    Wraps ``__init__`` and ``aclose`` with per-instance counters (without
    re-implementing the on_complete counter). Returns (created, close_counts)
    where close_counts is keyed by ``id(handle)``.
    """
    created: list[handle_mod.SpooledTranscriptHandle] = []
    close_counts: dict[int, int] = {}

    real_init = handle_mod.SpooledTranscriptHandle.__init__
    real_aclose = handle_mod.SpooledTranscriptHandle.aclose

    def spy_init(
        self: handle_mod.SpooledTranscriptHandle,
        *args: object,
        **kwargs: object,
    ) -> None:
        real_init(self, *args, **kwargs)  # type: ignore[arg-type]
        created.append(self)
        close_counts[id(self)] = 0

    async def spy_aclose(self: handle_mod.SpooledTranscriptHandle) -> None:
        close_counts[id(self)] = close_counts.get(id(self), 0) + 1
        await real_aclose(self)

    monkeypatch.setattr(handle_mod.SpooledTranscriptHandle, "__init__", spy_init)
    monkeypatch.setattr(handle_mod.SpooledTranscriptHandle, "aclose", spy_aclose)
    return created, close_counts


@scanner(name="streaming_lead_scanner", messages="all")
def streaming_lead_scanner_factory() -> Scanner[Transcript]:
    """Handle-capable llm_scanner (static question) -- runs as the lead job."""
    return llm_scanner(question="Is this conversation helpful?", answer="boolean")


@scanner(name="streaming_follower_scanner", messages="all")
def streaming_follower_scanner_factory() -> Scanner[Transcript]:
    """Handle-capable llm_scanner (static question) -- runs as a follower job.

    Identical ``messages="all"`` content filter to the lead so streaming
    eligibility holds and both share one union-filtered handle.
    """
    return llm_scanner(question="Is this conversation coherent?", answer="boolean")


@pytest.mark.parametrize(
    "scanner_names",
    [
        pytest.param(["streaming_lead_scanner"], id="single_scanner"),
        pytest.param(
            ["streaming_lead_scanner", "streaming_follower_scanner"],
            id="lead_and_follower",
        ),
    ],
)
def test_scan_e2e_through_streaming_seam(
    monkeypatch: pytest.MonkeyPatch, scanner_names: list[str]
) -> None:
    """A real scan over eval logs must stream and produce correct results.

    Handle-capable scanners share one spooled handle per transcript. We
    verify (1) each scanner records a result per transcript, and (2) the
    streaming path ran: one ``SpooledTranscriptHandle`` per transcript was
    created and each was closed exactly once (exercising the real
    lead+follower ``on_complete`` counter; the single-scanner case covers
    the lead-only fallback where remaining starts at 1).
    """
    limit = 2
    factories = {
        "streaming_lead_scanner": streaming_lead_scanner_factory,
        "streaming_follower_scanner": streaming_follower_scanner_factory,
    }

    # Force the eval_log backend to choose the spooled path for every file.
    monkeypatch.setattr("inspect_scout._util.constants.SPOOL_THRESHOLD_BYTES", 0)

    created, close_counts = _spy_spooled_handles(monkeypatch)

    # Enough mock responses for all scanners across all scanned transcripts.
    mock_responses = [
        ModelOutput.from_content(
            model="mockllm",
            content=f"Reasoning about [M2].\n\nANSWER: {'yes' if i % 2 else 'no'}",
        )
        for i in range(limit * len(scanner_names) * 4)
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        status = scan(
            scanners=[factories[name]() for name in scanner_names],
            transcripts=transcripts_from(LOGS_DIR),
            scans=tmpdir,
            limit=limit,
            max_processes=1,  # in-process so the monkeypatched spies apply
            model="mockllm/model",
            model_args={"custom_outputs": mock_responses},
            display="none",
        )

        assert status.complete
        assert status.location is not None

        for scanner_name in scanner_names:
            results = scan_results_df(status.location, scanner=scanner_name)
            df = results.scanners[scanner_name]
            assert len(df) == limit
            assert "value" in df.columns
            assert "explanation" in df.columns
            assert all(isinstance(v, bool) for v in df["value"].tolist())

    # The streaming path was actually exercised.
    assert len(created) >= 1, "no SpooledTranscriptHandle was created -- not streaming"
    # One shared handle per transcript => one per scanned transcript.
    assert len(created) == limit

    # Each spooled handle closed exactly once by the real on_complete counter.
    for h in created:
        assert close_counts[id(h)] == 1, (
            f"handle closed {close_counts[id(h)]} times, expected exactly 1"
        )


@scanner(name="streaming_events_scanner", events="all")
def streaming_events_scanner_factory() -> Scanner[Transcript]:
    """Events-content llm_scanner.

    Exercises the two-pass event streaming seam (`stream_timeline_messages`)
    rather than the messages-only path covered by the scanners above.
    """
    return llm_scanner(
        question="Did the agent use any tools?",
        answer="boolean",
        content=TranscriptContent(events="all"),
    )


def _mock_responses(n: int) -> list[ModelOutput]:
    return [
        ModelOutput.from_content(model="mockllm", content="Reasoning.\n\nANSWER: yes")
        for _ in range(n)
    ]


def test_scan_e2e_events_through_streaming_seam(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """An events-content llm_scanner scan streams through a spooled handle.

    Exercises `stream_timeline_messages`'s two-pass stub skeleton and
    produces the same result as a materialized control run over the same
    database with no threshold override.
    """
    db_location = tmp_path / "transcripts_db"
    db_location.mkdir()

    async def _seed() -> None:
        db = ParquetTranscriptsDB(str(db_location))
        await db.connect()
        try:
            await db.insert([agentic_transcript()])
        finally:
            await db.disconnect()

    anyio.run(_seed)

    created, close_counts = _spy_spooled_handles(monkeypatch)
    monkeypatch.setattr("inspect_scout._util.constants.SPOOL_THRESHOLD_BYTES", 0)

    with tempfile.TemporaryDirectory() as tmpdir:
        status = scan(
            scanners=[streaming_events_scanner_factory()],
            transcripts=transcripts_from(str(db_location)),
            scans=tmpdir,
            max_processes=1,  # in-process so the monkeypatched spies apply
            model="mockllm/model",
            model_args={"custom_outputs": _mock_responses(6)},
            display="none",
        )
        assert status.complete
        assert status.location is not None

        results = scan_results_df(status.location, scanner="streaming_events_scanner")
        df = results.scanners["streaming_events_scanner"]
        assert len(df) == 1
        streamed_values = df["value"].tolist()

    # The streaming path was actually exercised.
    assert len(created) == 1, "no SpooledTranscriptHandle was created -- not streaming"
    assert close_counts[id(created[0])] == 1

    # Control run: same database, same scanner, no threshold override ->
    # small agentic fixture content uses MaterializedTranscriptHandle.
    monkeypatch.undo()
    with tempfile.TemporaryDirectory() as tmpdir:
        control_status = scan(
            scanners=[streaming_events_scanner_factory()],
            transcripts=transcripts_from(str(db_location)),
            scans=tmpdir,
            max_processes=1,
            model="mockllm/model",
            model_args={"custom_outputs": _mock_responses(6)},
            display="none",
        )
        assert control_status.complete
        assert control_status.location is not None

        control_results = scan_results_df(
            control_status.location, scanner="streaming_events_scanner"
        )
        control_df = control_results.scanners["streaming_events_scanner"]
        control_values = control_df["value"].tolist()

    assert streamed_values == control_values


@scanner(name="attachment_scanner", messages="all", events="all")
def attachment_scanner_factory() -> Scanner[Transcript]:
    """Messages+events llm_scanner over an attachment-bearing eval log."""
    return llm_scanner(
        question="Is this conversation helpful?",
        answer="boolean",
        content=TranscriptContent(messages="all", events="all"),
    )


# The one example log whose samples externalize content as `attachment://`
# refs -- inspect_ai does that for any text value over 100 chars, so the
# recorded events are full of refs the reader has to resolve.
_ATTACHMENT_LOG = LOGS_DIR / (
    "2025-09-23T08-09-58-04-00_theory-of-mind_bbB4eRCx2rFJLyPH42Cj9r.eval"
)


def _scan_input_column(monkeypatch: pytest.MonkeyPatch, *, spool_threshold: int) -> str:
    """`scan_results_df`'s `input` value for a one-transcript scan."""
    monkeypatch.setattr(
        "inspect_scout._util.constants.SPOOL_THRESHOLD_BYTES", spool_threshold
    )
    with tempfile.TemporaryDirectory() as tmpdir:
        status = scan(
            scanners=[attachment_scanner_factory()],
            transcripts=transcripts_from(str(_ATTACHMENT_LOG)),
            scans=tmpdir,
            limit=1,
            max_processes=1,  # in-process so the monkeypatched threshold applies
            model="mockllm/model",
            model_args={"custom_outputs": _mock_responses(40)},
            display="none",
        )
        assert status.complete
        assert status.location is not None
        results = scan_results_df(status.location, scanner="attachment_scanner")
        return str(results.scanners["attachment_scanner"]["input"].tolist()[0])


def test_recorded_input_resolves_attachments_like_materialized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A streamed scan's recorded transcript must be readable.

    The pooled passthrough copies events out of the spool with their
    `attachment://<hash>` refs intact and ships the lookup table inside
    `input_data`, which `scan_results_df` drops. If nothing resolves those
    refs on the read path, every externalized value (any text over 100
    chars: system prompts, model output, tool results) reaches the caller of
    this public API as a dangling hash.
    """
    created, _ = _spy_spooled_handles(monkeypatch)

    streamed_input = _scan_input_column(monkeypatch, spool_threshold=0)
    assert created, "no SpooledTranscriptHandle was created -- not streaming"

    # Control: a threshold nothing can exceed forces the materialized path.
    created.clear()
    control_input = _scan_input_column(monkeypatch, spool_threshold=2**62)
    assert not created, "control run streamed -- not a materialized comparison"

    assert "attachment://" not in streamed_input
    streamed = json.loads(streamed_input)
    control = json.loads(control_input)
    assert streamed["messages"] == control["messages"]
    assert streamed["events"] == control["events"]
