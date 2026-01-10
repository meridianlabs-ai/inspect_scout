"""End-to-end tests for the validation feature."""

import json
import tempfile
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any, Sequence

import pytest
from inspect_ai.event import Event
from inspect_ai.model import ChatMessage
from inspect_scout import (
    Result,
    Scanner,
    ValidationCase,
    ValidationSet,
    loader,
    scan,
    scanner,
)
from inspect_scout._scanner.loader import Loader
from inspect_scout._scanresults import scan_results_db, scan_results_df
from inspect_scout._transcript.factory import transcripts_from
from inspect_scout._transcript.types import Transcript
from pydantic import JsonValue

# Test data location
LOGS_DIR = Path(__file__).parent / "recorder" / "logs"


# ============================================================================
# Helper Functions
# ============================================================================


async def get_n_transcript_ids(n: int) -> list[str]:
    """Get first n transcript IDs from test logs."""
    transcripts = transcripts_from(LOGS_DIR)
    async with transcripts.reader() as tr:
        index_list = [info async for info in tr.index()]
        return [info.transcript_id for info in index_list[:n]]


def create_validation_set(
    transcript_ids: list[str],
    targets: list[Any],
    predicate: str = "eq",
) -> ValidationSet:
    """Helper to create a ValidationSet from transcript IDs and targets."""
    assert len(transcript_ids) == len(targets), (
        "transcript_ids and targets must have same length"
    )
    return ValidationSet(
        cases=[
            ValidationCase(id=tid, target=target)
            for tid, target in zip(transcript_ids, targets, strict=True)
        ],
        predicate=predicate,  # type: ignore[arg-type]
    )


# ============================================================================
# Scanner Factories for Testing Validation
# ============================================================================


@scanner(name="bool_scanner", messages="all")
def bool_scanner_factory() -> Scanner[Transcript]:
    """Scanner that returns boolean values based on transcript ID hash."""

    async def scan_transcript(transcript: Transcript) -> Result:
        # Return True/False based on whether transcript ID hash is even/odd
        value = hash(transcript.transcript_id) % 2 == 0
        return Result(
            value=value,
            explanation=f"Bool scanner processed {transcript.transcript_id}: {value}",
        )

    return scan_transcript


@scanner(name="int_scanner", messages="all")
def int_scanner_factory() -> Scanner[Transcript]:
    """Scanner that returns integer values based on transcript ID hash."""

    async def scan_transcript(transcript: Transcript) -> Result:
        # Return int value based on transcript ID hash modulo 100
        value = abs(hash(transcript.transcript_id)) % 100
        return Result(
            value=value,
            explanation=f"Int scanner processed {transcript.transcript_id}: {value}",
        )

    return scan_transcript


@scanner(name="str_scanner", messages="all")
def str_scanner_factory() -> Scanner[Transcript]:
    """Scanner that returns string values."""

    async def scan_transcript(transcript: Transcript) -> Result:
        # Return string value based on transcript ID
        value = f"result_{transcript.transcript_id[:8]}"
        return Result(
            value=value,
            explanation=f"String scanner processed {transcript.transcript_id}",
        )

    return scan_transcript


@scanner(name="dict_scanner", messages="all")
def dict_scanner_factory() -> Scanner[Transcript]:
    """Scanner that returns dict values with multiple keys."""

    async def scan_transcript(transcript: Transcript) -> Result:
        # Return dict with multiple dimensions
        tid_hash = abs(hash(transcript.transcript_id))
        value: JsonValue = {
            "score_a": tid_hash % 100,
            "score_b": (tid_hash // 100) % 100,
            "flag": tid_hash % 2 == 0,
        }
        return Result(
            value=value,
            explanation=f"Dict scanner processed {transcript.transcript_id}",
        )

    return scan_transcript


@scanner(name="validation_scanner_a", messages="all")
def validation_scanner_a_factory() -> Scanner[Transcript]:
    """Scanner A for multi-scanner validation tests."""

    async def scan_transcript(transcript: Transcript) -> Result:
        return Result(
            value=True,
            explanation=f"Scanner A processed {transcript.transcript_id}",
        )

    return scan_transcript


@scanner(name="validation_scanner_b", messages="all")
def validation_scanner_b_factory() -> Scanner[Transcript]:
    """Scanner B for multi-scanner validation tests."""

    async def scan_transcript(transcript: Transcript) -> Result:
        return Result(
            value=False,
            explanation=f"Scanner B processed {transcript.transcript_id}",
        )

    return scan_transcript


# ============================================================================
# Basic Validation Tests
# ============================================================================


@pytest.mark.asyncio
async def test_validation_basic_single_target_e2e() -> None:
    """Test basic validation: scan with validation → scan_results with validation columns."""
    # Get test transcript IDs
    transcript_ids = await get_n_transcript_ids(3)

    # Create validation set - we need to know what the scanner will return
    # The bool_scanner returns True if transcript ID hash is even
    targets = [hash(tid) % 2 == 0 for tid in transcript_ids]
    validation = create_validation_set(transcript_ids, targets, predicate="eq")

    # Run scan with validation
    with tempfile.TemporaryDirectory() as tmpdir:
        scan_result = scan(
            scanners=[bool_scanner_factory()],
            transcripts=transcripts_from(LOGS_DIR),
            validation=validation,
            scans=tmpdir,
            limit=3,  # Only scan 3 transcripts for efficiency
            max_processes=1,  # hash() is not stable across processes
        )

        # Get results using scan_results
        results = scan_results_df(scan_result.location, scanner="bool_scanner")
        df = results.scanners["bool_scanner"]

        # Verify validation columns exist
        assert "validation_target" in df.columns, (
            "validation_target column should exist"
        )
        assert "validation_result" in df.columns, (
            "validation_result column should exist"
        )

        # Verify we have the right number of results
        assert len(df) == 3, f"Expected 3 results, got {len(df)}"

        # Verify all validations passed (since targets match scanner output)
        # Note: Only rows with validation will have non-null validation_result
        df_validated = df[df["validation_result"].notna()]
        validation_results = df_validated["validation_result"].tolist()
        assert all(validation_results), (
            f"All validations should pass but got: {validation_results}"
        )

        # Verify that validated rows have correct target values
        # (targets match what the bool_scanner would return for those transcript IDs)
        for _, row in df_validated.iterrows():
            tid = row["transcript_id"]
            # values can be stored as native values (since there is also a value_type column), but validation_targets is alway a json encoded value (string or dict)
            expected_value = True if hash(tid) % 2 == 0 else False
            expected_target = "true" if hash(tid) % 2 == 0 else "false"
            assert row["value"] == expected_value, (
                f"Scanner value for {tid} should be {expected_value}"
            )
            assert row["validation_target"] == expected_target, (
                f"Validation target for {tid} should be {expected_target}"
            )


@pytest.mark.asyncio
async def test_validation_multi_target_dict_e2e() -> None:
    """Test validation with dict targets (multi-dimensional validation)."""
    # Get test transcript IDs
    transcript_ids = await get_n_transcript_ids(3)

    # Create dict targets that match what dict_scanner will return
    targets: list[JsonValue] = []
    for tid in transcript_ids:
        tid_hash = abs(hash(tid))
        targets.append(
            {
                "score_a": tid_hash % 100,
                "score_b": (tid_hash // 100) % 100,
                "flag": tid_hash % 2 == 0,
            }
        )

    validation = ValidationSet(
        cases=[
            ValidationCase(id=tid, target=target)
            for tid, target in zip(transcript_ids, targets, strict=True)
        ],
        predicate="eq",
    )

    # Run scan with validation
    with tempfile.TemporaryDirectory() as tmpdir:
        scan_result = scan(
            scanners=[dict_scanner_factory()],
            transcripts=transcripts_from(LOGS_DIR),
            validation=validation,
            scans=tmpdir,
            limit=3,  # Only scan 3 transcripts for efficiency
            max_processes=1,  # hash() is not stable across processes
        )

        # Get results
        results = scan_results_df(scan_result.location, scanner="dict_scanner")
        df = results.scanners["dict_scanner"]

        # Verify validation columns exist
        assert "validation_target" in df.columns
        assert "validation_result" in df.columns

        # Verify individual validation_result_{key} columns exist
        assert "validation_result_score_a" in df.columns, (
            "validation_result_score_a column should exist for dict targets"
        )
        assert "validation_result_score_b" in df.columns, (
            "validation_result_score_b column should exist for dict targets"
        )
        assert "validation_result_flag" in df.columns, (
            "validation_result_flag column should exist for dict targets"
        )

        # Verify all individual validations passed
        assert all(df["validation_result_score_a"]), (
            "score_a validations should all pass"
        )
        assert all(df["validation_result_score_b"]), (
            "score_b validations should all pass"
        )
        assert all(df["validation_result_flag"]), "flag validations should all pass"

        # Verify validation_result contains JSON dict
        validation_result = df["validation_result"].iloc[0]
        assert isinstance(validation_result, str), (
            "validation_result should be JSON-encoded string for dict targets"
        )
        assert "score_a" in validation_result, (
            "validation_result JSON should contain score_a"
        )


@pytest.mark.asyncio
async def test_validation_multiple_scanners_e2e() -> None:
    """Test validation with multiple scanners each having their own validation set."""
    # Get test transcript IDs
    transcript_ids = await get_n_transcript_ids(3)

    # Create different validation sets for each scanner
    validation_a = create_validation_set(
        transcript_ids, [True, True, True], predicate="eq"
    )
    validation_b = create_validation_set(
        transcript_ids, [False, False, False], predicate="eq"
    )

    # Pass validation as dict mapping scanner names to validation sets
    validation_dict = {
        "validation_scanner_a": validation_a,
        "validation_scanner_b": validation_b,
    }

    # Run scan with multiple scanners and their validation sets
    with tempfile.TemporaryDirectory() as tmpdir:
        scan_result = scan(
            scanners=[
                validation_scanner_a_factory(),
                validation_scanner_b_factory(),
            ],
            transcripts=transcripts_from(LOGS_DIR),
            validation=validation_dict,
            scans=tmpdir,
            limit=3,  # Only scan 3 transcripts for efficiency
        )

        # Get results for scanner A
        results_a = scan_results_df(
            scan_result.location, scanner="validation_scanner_a"
        )
        df_a = results_a.scanners["validation_scanner_a"]
        assert "validation_target" in df_a.columns
        assert "validation_result" in df_a.columns
        assert all(df_a["validation_target"] == "true")  # noqa: E712
        assert all(df_a["validation_result"]), "Scanner A validations should all pass"

        # Get results for scanner B
        results_b = scan_results_df(
            scan_result.location, scanner="validation_scanner_b"
        )
        df_b = results_b.scanners["validation_scanner_b"]
        assert "validation_target" in df_b.columns
        assert "validation_result" in df_b.columns
        assert all(df_b["validation_target"] == "false")  # noqa: E712
        assert all(df_b["validation_result"]), "Scanner B validations should all pass"


@pytest.mark.asyncio
async def test_validation_different_predicates_e2e() -> None:
    """Test validation with different predicates (gt, contains, etc)."""
    # Get test transcript IDs
    transcript_ids = await get_n_transcript_ids(3)

    # Create validation set with 'gt' predicate
    # int_scanner returns values 0-99, so we set targets that will pass
    targets = [50, 50, 50]  # All scanner results should be > 50 or < 50
    validation = create_validation_set(transcript_ids, targets, predicate="gt")

    # Run scan with validation
    with tempfile.TemporaryDirectory() as tmpdir:
        scan_result = scan(
            scanners=[int_scanner_factory()],
            transcripts=transcripts_from(LOGS_DIR),
            validation=validation,
            scans=tmpdir,
            limit=3,  # Only scan 3 transcripts for efficiency
        )

        # Get results
        results = scan_results_df(scan_result.location, scanner="int_scanner")
        df = results.scanners["int_scanner"]

        # Verify validation columns exist
        assert "validation_target" in df.columns
        assert "validation_result" in df.columns

        # Verify targets are all 50
        assert all(df["validation_target"] == "50"), "All targets should be 50"

        # Verify validation results are boolean (some pass, some fail depending on hash)
        validation_results = df["validation_result"].tolist()
        # verify that if each value is deserialized from json it is a boolean
        deserialized_results = [
            json.loads(v) if isinstance(v, str) else v for v in validation_results
        ]
        assert all(isinstance(v, bool) for v in deserialized_results), (
            "All validation results should be boolean after deserialization"
        )


@pytest.mark.asyncio
async def test_validation_partial_coverage_e2e() -> None:
    """Test validation when only subset of transcripts have validation cases."""
    # Get test transcript IDs - we'll validate only some of them
    all_transcript_ids = await get_n_transcript_ids(5)

    # Create validation set for only first 3 transcripts
    validated_ids = all_transcript_ids[:3]
    targets = [hash(tid) % 2 == 0 for tid in validated_ids]
    validation = create_validation_set(validated_ids, targets, predicate="eq")

    # Run scan - all 5 transcripts will be scanned, but only 3 have validation
    with tempfile.TemporaryDirectory() as tmpdir:
        scan_result = scan(
            scanners=[bool_scanner_factory()],
            transcripts=transcripts_from(LOGS_DIR),
            validation=validation,
            scans=tmpdir,
            limit=5,  # Scan 5 transcripts, but only 3 have validation
        )

        # Get all results
        results = scan_results_df(scan_result.location, scanner="bool_scanner")
        df = results.scanners["bool_scanner"]

        # Verify we have 5 total results
        assert len(df) == 5, f"Expected 5 results, got {len(df)}"

        # Verify validation columns exist
        assert "validation_target" in df.columns
        assert "validation_result" in df.columns

        # Get rows with and without validation
        df_with_validation = df[df["transcript_id"].isin(validated_ids)]
        df_without_validation = df[~df["transcript_id"].isin(validated_ids)]

        # Verify validated transcripts have non-null validation data
        assert len(df_with_validation) == 3
        assert all(df_with_validation["validation_target"].notna()), (
            "Validated transcripts should have non-null validation_target"
        )
        assert all(df_with_validation["validation_result"].notna()), (
            "Validated transcripts should have non-null validation_result"
        )

        # Verify non-validated transcripts have null validation data
        assert len(df_without_validation) == 2
        assert all(df_without_validation["validation_target"].isna()), (
            "Non-validated transcripts should have null validation_target"
        )
        assert all(df_without_validation["validation_result"].isna()), (
            "Non-validated transcripts should have null validation_result"
        )


# ============================================================================
# Advanced Validation Tests
# ============================================================================


@pytest.mark.asyncio
async def test_validation_with_custom_predicate_e2e() -> None:
    """Test validation with a custom callable predicate."""
    # Get test transcript IDs
    transcript_ids = await get_n_transcript_ids(3)

    # Define custom predicate function
    async def custom_within_range(result: Result, target: Any) -> bool:
        """Check if result value is within 10 of target."""
        if not isinstance(result.value, (int, float)):
            return False
        if not isinstance(target, (int, float)):
            return False
        return abs(result.value - target) <= 10

    # Create validation set with custom predicate
    targets = [50, 50, 50]
    validation = ValidationSet(
        cases=[
            ValidationCase(id=tid, target=target)
            for tid, target in zip(transcript_ids, targets, strict=True)
        ],
        predicate=custom_within_range,
    )

    # Run scan with validation
    with tempfile.TemporaryDirectory() as tmpdir:
        scan_result = scan(
            scanners=[int_scanner_factory()],
            transcripts=transcripts_from(LOGS_DIR),
            validation=validation,
            scans=tmpdir,
            limit=3,  # Only scan 3 transcripts for efficiency
        )

        # Get results
        results = scan_results_df(scan_result.location, scanner="int_scanner")
        df = results.scanners["int_scanner"]

        # Verify validation columns exist
        assert "validation_target" in df.columns
        assert "validation_result" in df.columns

        # Verify validation results are boolean
        validation_results = df["validation_result"].tolist()
        deserialized_results = [
            json.loads(v) if isinstance(v, str) else v for v in validation_results
        ]
        assert all(isinstance(v, bool) for v in deserialized_results), (
            "All validation results should be boolean"
        )


@pytest.mark.asyncio
async def test_validation_failing_cases_e2e() -> None:
    """Test validation when results don't match targets (failing validations)."""
    # Get test transcript IDs
    transcript_ids = await get_n_transcript_ids(3)

    # Create validation set with WRONG targets (opposite of what scanner returns)
    correct_targets = [hash(tid) % 2 == 0 for tid in transcript_ids]
    wrong_targets = [not t for t in correct_targets]  # Flip all targets
    validation = create_validation_set(transcript_ids, wrong_targets, predicate="eq")

    # Run scan with validation
    with tempfile.TemporaryDirectory() as tmpdir:
        scan_result = scan(
            scanners=[bool_scanner_factory()],
            transcripts=transcripts_from(LOGS_DIR),
            validation=validation,
            scans=tmpdir,
            limit=3,  # Only scan 3 transcripts for efficiency
            max_processes=1,  # hash() is not stable across processes
        )

        # Get results
        results = scan_results_df(scan_result.location, scanner="bool_scanner")
        df = results.scanners["bool_scanner"]

        # Verify validation columns exist
        assert "validation_target" in df.columns
        assert "validation_result" in df.columns

        # Verify all validations FAILED (since we flipped all targets)
        validation_results = df["validation_result"].tolist()
        deserialized_results = [
            json.loads(v) if isinstance(v, str) else v for v in validation_results
        ]
        assert all(v == False for v in deserialized_results), (  # noqa: E712
            f"All validations should fail but got: {deserialized_results}"
        )


@pytest.mark.asyncio
async def test_validation_database_columns_e2e() -> None:
    """Test that validation columns are correctly accessible via scan_results_db."""
    # Get test transcript IDs
    transcript_ids = await get_n_transcript_ids(3)

    # Create validation set
    targets = [hash(tid) % 2 == 0 for tid in transcript_ids]
    validation = create_validation_set(transcript_ids, targets, predicate="eq")

    # Run scan with validation
    with tempfile.TemporaryDirectory() as tmpdir:
        scan_result = scan(
            scanners=[bool_scanner_factory()],
            transcripts=transcripts_from(LOGS_DIR),
            validation=validation,
            scans=tmpdir,
            limit=3,  # Only scan 3 transcripts for efficiency
        )

        # Access database directly
        db = scan_results_db(scan_result.location)
        try:
            # Verify table exists
            tables = db.conn.execute("SHOW TABLES").fetchall()
            table_names = [t[0] for t in tables]
            assert "bool_scanner" in table_names

            # Query validation columns
            query = """
                SELECT
                    transcript_id,
                    value,
                    validation_target,
                    validation_result
                FROM bool_scanner
                ORDER BY transcript_id
            """
            df = db.conn.execute(query).fetchdf()

            # Verify columns exist and have expected types
            assert "validation_target" in df.columns
            assert "validation_result" in df.columns

            # Verify data integrity
            assert len(df) == 3
            assert all(df["validation_result"].notna())
            assert all(df["validation_target"].notna())

        finally:
            db.conn.close()


# ============================================================================
# Message and Event-Based Scanner Tests
# ============================================================================


@scanner(name="message_scanner", messages=["user"])
def message_scanner_factory() -> Scanner[ChatMessage]:
    """Scanner that processes individual user messages."""

    async def scan_message(message: ChatMessage) -> Result:
        # Return boolean based on message length
        value = len(message.text) > 50
        return Result(
            value=value,
            explanation=f"Message scanner: length={len(message.text)}, long={value}",
        )

    return scan_message


@scanner(name="event_scanner", events=["model"])
def event_scanner_factory() -> Scanner[Event]:
    """Scanner that processes model events."""

    async def scan_event(event: Event) -> Result:
        # Return boolean based on event type
        value = event.event == "model"
        return Result(
            value=value,
            explanation=f"Event scanner: event={event.event}",
        )

    return scan_event


@pytest.mark.asyncio
async def test_validation_message_based_scanner_e2e() -> None:
    """Test validation with message-based scanner."""
    # First pass: Run scan without validation to get message IDs
    with tempfile.TemporaryDirectory() as tmpdir:
        scan_result = scan(
            scanners=[message_scanner_factory()],
            transcripts=transcripts_from(LOGS_DIR),
            scans=tmpdir,
            limit=1,  # Only scan 1 transcript
        )

        # Get results from first scan
        results = scan_results_df(scan_result.location, scanner="message_scanner")
        df_first = results.scanners["message_scanner"]

        # Verify we have message-based results
        assert len(df_first) > 0, "Should have processed some messages"
        assert all(df_first["input_type"] == "message"), (
            "Input type should be 'message'"
        )

        # Get first 3 message IDs from the results
        message_ids = []
        for input_ids_json in df_first["input_ids"].head(3):
            ids = json.loads(input_ids_json)
            if isinstance(ids, list):
                message_ids.extend(ids)
            else:
                message_ids.append(ids)

    # Second pass: Run scan with validation for those message IDs
    # Create validation set - target True for messages longer than 50 chars
    validation = ValidationSet(
        cases=[ValidationCase(id=msg_id, target=True) for msg_id in message_ids],
        predicate="eq",
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        scan_result = scan(
            scanners=[message_scanner_factory()],
            transcripts=transcripts_from(LOGS_DIR),
            validation=validation,
            scans=tmpdir,
            limit=1,  # Scan same transcript
        )

        # Get results with validation
        results = scan_results_df(scan_result.location, scanner="message_scanner")
        df = results.scanners["message_scanner"]

        # Verify validation columns exist
        assert "validation_target" in df.columns
        assert "validation_result" in df.columns

        # Verify we have results with validation data
        df_validated = df[df["validation_result"].notna()]
        assert len(df_validated) > 0, "Should have at least some validated messages"

        # Verify input_type is "message"
        assert all(df_validated["input_type"] == "message"), (
            "Input type should be 'message' for message-based scanner"
        )

        # Verify validation targets are all True (as we set them)
        validation_targets = df_validated["validation_target"].tolist()
        deserialized_targets = [
            json.loads(v) if isinstance(v, str) else v for v in validation_targets
        ]
        assert all(t == True for t in deserialized_targets), (  # noqa: E712
            "All validation targets should be True"
        )

        # Verify validation results are boolean
        validation_results = df_validated["validation_result"].tolist()
        deserialized_results = [
            json.loads(v) if isinstance(v, str) else v for v in validation_results
        ]
        assert all(isinstance(v, bool) for v in deserialized_results), (
            "All validation results should be boolean"
        )


@pytest.mark.asyncio
async def test_validation_event_based_scanner_e2e() -> None:
    """Test validation with event-based scanner."""
    # First pass: Run scan without validation to get event IDs
    with tempfile.TemporaryDirectory() as tmpdir:
        scan_result = scan(
            scanners=[event_scanner_factory()],
            transcripts=transcripts_from(LOGS_DIR),
            scans=tmpdir,
            limit=1,  # Only scan 1 transcript
        )

        # Get results from first scan
        results = scan_results_df(scan_result.location, scanner="event_scanner")
        df_first = results.scanners["event_scanner"]

        # Verify we have event-based results
        assert len(df_first) > 0, "Should have processed some events"
        assert all(df_first["input_type"] == "event"), "Input type should be 'event'"

        # Get first 3 event IDs from the results
        event_ids = []
        for input_ids_json in df_first["input_ids"].head(3):
            ids = json.loads(input_ids_json)
            if isinstance(ids, list):
                event_ids.extend(ids)
            else:
                event_ids.append(ids)

    # Second pass: Run scan with validation for those event IDs
    # Create validation set - target True (since scanner checks event.event == "model")
    validation = ValidationSet(
        cases=[ValidationCase(id=evt_id, target=True) for evt_id in event_ids],
        predicate="eq",
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        scan_result = scan(
            scanners=[event_scanner_factory()],
            transcripts=transcripts_from(LOGS_DIR),
            validation=validation,
            scans=tmpdir,
            limit=1,  # Scan same transcript
        )

        # Get results with validation
        results = scan_results_df(scan_result.location, scanner="event_scanner")
        df = results.scanners["event_scanner"]

        # Verify validation columns exist
        assert "validation_target" in df.columns
        assert "validation_result" in df.columns

        # Verify we have results with validation data
        df_validated = df[df["validation_result"].notna()]
        assert len(df_validated) > 0, "Should have at least some validated events"

        # Verify input_type is "event"
        assert all(df_validated["input_type"] == "event"), (
            "Input type should be 'event' for event-based scanner"
        )

        # Verify validation targets are all True (as we set them)
        validation_targets = df_validated["validation_target"].tolist()
        deserialized_targets = [
            json.loads(v) if isinstance(v, str) else v for v in validation_targets
        ]
        assert all(t == True for t in deserialized_targets), (  # noqa: E712
            "All validation targets should be True"
        )

        # Verify validation results are boolean
        validation_results = df_validated["validation_result"].tolist()
        deserialized_results = [
            json.loads(v) if isinstance(v, str) else v for v in validation_results
        ]
        assert all(isinstance(v, bool) for v in deserialized_results), (
            "All validation results should be boolean"
        )


# ============================================================================
# Message Pairs with List IDs Test
# ============================================================================


# Custom loader factory that yields user/assistant message pairs
@loader(name="message_pair_loader", messages="all")
def message_pair_loader_factory() -> Loader[Sequence[ChatMessage]]:
    """Factory that returns a loader for user/assistant message pairs."""

    async def load(transcript: Transcript) -> AsyncIterator[Sequence[ChatMessage]]:
        """Load pairs of consecutive user/assistant messages."""
        messages = transcript.messages
        for i in range(len(messages) - 1):
            if messages[i].role == "user" and messages[i + 1].role == "assistant":
                yield [messages[i], messages[i + 1]]

    return load


# Scanner that processes message pairs
@scanner(name="pair_scanner", loader=message_pair_loader_factory())
def pair_scanner_factory() -> Scanner[Sequence[ChatMessage]]:
    """Scanner that processes user/assistant message pairs."""

    async def scan_pair(messages: Sequence[ChatMessage]) -> Result:
        # Return True if user message is short and assistant message is long
        user_msg = messages[0]
        assistant_msg = messages[1]
        value = len(user_msg.text) < 50 and len(assistant_msg.text) > 50
        return Result(
            value=value,
            explanation=f"Pair scanner: user_len={len(user_msg.text)}, assistant_len={len(assistant_msg.text)}",
        )

    return scan_pair


@pytest.mark.asyncio
async def test_validation_message_pairs_with_list_ids_e2e() -> None:
    """Test validation with custom loader for message pairs and list IDs."""
    # First pass: Run scan without validation to get message pair IDs
    with tempfile.TemporaryDirectory() as tmpdir:
        scan_result = scan(
            scanners=[pair_scanner_factory()],
            transcripts=transcripts_from(LOGS_DIR),
            scans=tmpdir,
            limit=1,  # Only scan 1 transcript
        )

        # Get results from first scan
        results = scan_results_df(scan_result.location, scanner="pair_scanner")
        df_first = results.scanners["pair_scanner"]

        # Verify we have message pair results
        assert len(df_first) > 0, "Should have processed some message pairs"
        assert all(df_first["input_type"] == "messages"), (
            "Input type should be 'messages' (plural) for message pairs"
        )

        # Get first 3 message pair IDs from the results
        message_pair_ids: list[list[str]] = []
        for input_ids_json in df_first["input_ids"].head(3):
            ids = json.loads(input_ids_json)
            # For message pairs, input_ids should be a list of 2 IDs
            assert isinstance(ids, list), "input_ids should be a list for message pairs"
            assert len(ids) == 2, "input_ids should contain 2 message IDs for pairs"
            message_pair_ids.append(ids)

    # Second pass: Run scan with validation for those message pairs
    # Create validation set with list IDs
    validation = ValidationSet(
        cases=[
            ValidationCase(id=pair_ids, target=True) for pair_ids in message_pair_ids
        ],
        predicate="eq",
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        scan_result = scan(
            scanners=[pair_scanner_factory()],
            transcripts=transcripts_from(LOGS_DIR),
            validation=validation,
            scans=tmpdir,
            limit=1,  # Scan same transcript
        )

        # Get results with validation
        results = scan_results_df(scan_result.location, scanner="pair_scanner")
        df = results.scanners["pair_scanner"]

        # Verify validation columns exist
        assert "validation_target" in df.columns
        assert "validation_result" in df.columns

        # Verify we have results with validation data
        df_validated = df[df["validation_result"].notna()]
        assert len(df_validated) > 0, (
            "Should have at least some validated message pairs"
        )

        # Verify input_type is "messages" (plural)
        assert all(df_validated["input_type"] == "messages"), (
            "Input type should be 'messages' (plural) for message pairs"
        )

        # Verify input_ids contains lists of 2 IDs
        for input_ids_json in df_validated["input_ids"]:
            ids = json.loads(input_ids_json)
            assert isinstance(ids, list), "input_ids should be a list"
            assert len(ids) == 2, "input_ids should contain 2 IDs for message pairs"

        # Verify validation targets are all True (as we set them)
        validation_targets = df_validated["validation_target"].tolist()
        deserialized_targets = [
            json.loads(v) if isinstance(v, str) else v for v in validation_targets
        ]
        assert all(t == True for t in deserialized_targets), (  # noqa: E712
            "All validation targets should be True"
        )

        # Verify validation results are boolean
        validation_results = df_validated["validation_result"].tolist()
        deserialized_results = [
            json.loads(v) if isinstance(v, str) else v for v in validation_results
        ]
        assert all(isinstance(v, bool) for v in deserialized_results), (
            "All validation results should be boolean"
        )
