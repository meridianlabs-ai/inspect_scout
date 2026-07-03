"""End-to-end scan through the streaming (spooled handle) seam.

Forces every eval-log transcript through ``SpooledTranscriptHandle`` by
monkeypatching the streaming byte threshold to 0, runs a real ``scan()`` with
two handle-capable ``llm_scanner`` scanners (lead + follower), and asserts both
that results are recorded correctly and that the streaming path was actually
taken -- each shared spooled handle is created and closed exactly once per
transcript by the real ``on_complete`` counter in ``_scan.py``.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from inspect_ai.model import ModelOutput
from inspect_scout import Scanner, llm_scanner, scan, scanner
from inspect_scout._scanresults import scan_results_df
from inspect_scout._transcript import handle as handle_mod
from inspect_scout._transcript.factory import transcripts_from
from inspect_scout._transcript.types import Transcript

LOGS_DIR = Path(__file__).parent.parent.parent / "examples" / "scanner" / "logs"


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


def test_scan_e2e_through_streaming_seam(monkeypatch: pytest.MonkeyPatch) -> None:
    """A real scan over eval logs must stream and produce correct results.

    Two handle-capable scanners share one spooled handle per transcript. We
    verify (1) both scanners record a result per transcript, and (2) the
    streaming path ran: at least one ``SpooledTranscriptHandle`` was created
    and each created handle was closed exactly once (exercising the real
    lead+follower ``on_complete`` counter).
    """
    limit = 2

    # Force the eval_log backend to choose the spooled path for every file.
    monkeypatch.setattr("inspect_scout._util.constants.SPOOL_THRESHOLD_BYTES", 0)

    # Spy on SpooledTranscriptHandle create/close without re-implementing the
    # counter: wrap __init__ and aclose with per-instance counters.
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

    # Enough mock responses for both scanners across all scanned transcripts.
    mock_responses = [
        ModelOutput.from_content(
            model="mockllm",
            content=f"Reasoning about [M2].\n\nANSWER: {'yes' if i % 2 else 'no'}",
        )
        for i in range(limit * 2 * 4)
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        status = scan(
            scanners=[
                streaming_lead_scanner_factory(),
                streaming_follower_scanner_factory(),
            ],
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

        for scanner_name in ("streaming_lead_scanner", "streaming_follower_scanner"):
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
        # Post-close, the underlying StreamParseResult is released.
        assert h._result is None
        assert h._closed is True


def test_scan_e2e_single_handle_scanner_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Single handle-capable scanner still streams and closes its handle once.

    Fallback coverage for the lead-only (no follower) case: remaining starts
    at 1 and the single job's completion closes the handle.
    """
    limit = 2
    monkeypatch.setattr("inspect_scout._util.constants.SPOOL_THRESHOLD_BYTES", 0)

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

    mock_responses = [
        ModelOutput.from_content(model="mockllm", content="Yes.\n\nANSWER: yes")
        for _ in range(limit * 4)
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        status = scan(
            scanners=[streaming_lead_scanner_factory()],
            transcripts=transcripts_from(LOGS_DIR),
            scans=tmpdir,
            limit=limit,
            max_processes=1,
            model="mockllm/model",
            model_args={"custom_outputs": mock_responses},
            display="none",
        )
        assert status.complete
        assert status.location is not None

        results = scan_results_df(status.location, scanner="streaming_lead_scanner")
        df = results.scanners["streaming_lead_scanner"]
        assert len(df) == limit

    assert len(created) == limit
    for h in created:
        assert close_counts[id(h)] == 1
        assert h._result is None
