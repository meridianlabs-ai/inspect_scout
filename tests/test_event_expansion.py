"""Tests for event expansion in scan_results_df."""

import json
import tempfile
from pathlib import Path
from typing import Any

import pandas as pd
from inspect_ai.event._model import ModelEvent
from inspect_scout import Result, Scanner, scan, scanner
from inspect_scout._scanresults import _expand_events_in_df, scan_results_df
from inspect_scout._transcript.factory import transcripts_from
from inspect_scout._transcript.types import Transcript

LOGS_DIR = Path(__file__).parent.parent / "examples" / "scanner" / "logs"


@scanner(name="events_scanner", events=["model"])  # type: ignore[type-var]
def events_scanner_factory() -> Scanner[list[ModelEvent]]:
    """Scanner that consumes model events as list (triggers condensation)."""

    async def scan_events(events: list[ModelEvent]) -> Result:
        return Result(value=len(events), explanation="event count")

    return scan_events


@scanner(name="messages_scanner", messages="all")
def messages_scanner_factory() -> Scanner[Transcript]:
    """Scanner that consumes only messages (no condensation)."""

    async def scan_transcript(transcript: Transcript) -> Result:
        return Result(value=True, explanation="has messages")

    return scan_transcript


@scanner(name="transcript_scanner", messages="all", events="all")
def transcript_scanner_factory() -> Scanner[Transcript]:
    """Scanner that consumes messages+events (transcript with condensation)."""

    async def scan_transcript(transcript: Transcript) -> Result:
        return Result(value=len(transcript.events), explanation="event count")

    return scan_transcript


def _has_unresolved_refs(events: list[dict[str, Any]]) -> bool:
    """Check if any event has unresolved input_refs or call_refs."""
    for event in events:
        if event.get("input_refs") is not None:
            return True
        call = event.get("call")
        if call and call.get("call_refs") is not None:
            return True
    return False


def test_events_expanded_in_results_df() -> None:
    """Events-type inputs have refs resolved and input_data dropped."""
    with tempfile.TemporaryDirectory() as tmpdir:
        status = scan(
            scanners=[events_scanner_factory()],
            transcripts=transcripts_from(LOGS_DIR),
            scans=tmpdir,
            limit=1,
            max_processes=1,
        )

        results = scan_results_df(status.location, scanner="events_scanner")
        df = results.scanners["events_scanner"]

        assert "input_data" not in df.columns
        assert "input" in df.columns

        input_json = df["input"].iloc[0]
        events = json.loads(input_json)
        assert isinstance(events, list)
        assert not _has_unresolved_refs(events)


def test_transcript_input_expanded_in_results_df() -> None:
    """Transcript-type inputs have events expanded and input_data dropped."""
    with tempfile.TemporaryDirectory() as tmpdir:
        status = scan(
            scanners=[transcript_scanner_factory()],
            transcripts=transcripts_from(LOGS_DIR),
            scans=tmpdir,
            limit=1,
            max_processes=1,
        )

        results = scan_results_df(status.location, scanner="transcript_scanner")
        df = results.scanners["transcript_scanner"]

        assert "input_data" not in df.columns

        input_json = df["input"].iloc[0]
        transcript = json.loads(input_json)
        assert "events" in transcript
        assert not _has_unresolved_refs(transcript["events"])


def test_messages_only_scanner_no_errors() -> None:
    """Messages-only scanner has no input_data; expansion is a no-op."""
    with tempfile.TemporaryDirectory() as tmpdir:
        status = scan(
            scanners=[messages_scanner_factory()],
            transcripts=transcripts_from(LOGS_DIR),
            scans=tmpdir,
            limit=1,
            max_processes=1,
        )

        results = scan_results_df(status.location, scanner="messages_scanner")
        df = results.scanners["messages_scanner"]

        # input_data column should be dropped regardless
        assert "input_data" not in df.columns
        assert "input" in df.columns


def test_transcript_mode_also_expands() -> None:
    """rows='transcripts' should also expand condensed events."""
    with tempfile.TemporaryDirectory() as tmpdir:
        status = scan(
            scanners=[events_scanner_factory()],
            transcripts=transcripts_from(LOGS_DIR),
            scans=tmpdir,
            limit=1,
            max_processes=1,
        )

        results = scan_results_df(
            status.location, scanner="events_scanner", rows="transcripts"
        )
        df = results.scanners["events_scanner"]

        assert "input_data" not in df.columns

        input_json = df["input"].iloc[0]
        events = json.loads(input_json)
        assert not _has_unresolved_refs(events)


def test_expand_events_no_input_column() -> None:
    """DataFrame with input_data but without 'input' column should not raise."""
    df = pd.DataFrame({"scanner": ["s1"], "value": [42], "input_data": ["data"]})
    result = _expand_events_in_df(df)
    assert "input_data" not in result.columns
    assert "input" not in result.columns
