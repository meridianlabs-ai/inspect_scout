import asyncio
import json
import os
import shutil
import tempfile
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, nullcontext
from pathlib import Path
from typing import Any, NamedTuple

import pytest
from inspect_ai.log import transcript as inspect_transcript
from inspect_ai.model import ChatMessage, ModelOutput, get_model
from inspect_ai.model._chat_message import ChatMessageUser
from inspect_ai.util import span
from inspect_scout import (
    Loader,
    Result,
    Scanner,
    llm_scanner,
    loader,
    scan,
    scanner,
    transcripts_db,
)
from inspect_scout._scanresults import scan_results_df
from inspect_scout._transcript.factory import transcripts_from
from inspect_scout._transcript.types import Transcript

# Test data location
LOGS_DIR = Path(__file__).parent.parent.parent / "examples" / "scanner" / "logs"


def create_minimal_transcript(transcript_id: str, index: int) -> Transcript:
    """Create a minimal transcript for testing."""
    return Transcript(
        transcript_id=transcript_id,
        source_type="test",
        source_id=f"source-{index // 100}",
        source_uri=f"test://uri/{index}",
        metadata={"index": index},
        messages=[ChatMessageUser(content=f"Test message {index}")],
        events=[],
    )


@scanner(name="simple_scanner", messages="all")
def simple_scanner_factory() -> Scanner[Transcript]:
    """Scanner that returns simple values for testing."""

    async def scan_transcript(transcript: Transcript) -> Result:
        # Return a simple result based on transcript ID
        value = len(transcript.transcript_id) % 2 == 0
        return Result(
            value=value,
            explanation=f"Scanned transcript {transcript.transcript_id[:8]}",
        )

    return scan_transcript


@scanner(name="llm_test_scanner", messages="all")
def llm_scanner_factory() -> Scanner[Transcript]:
    """LLM scanner that uses mockllm for testing."""
    return llm_scanner(question="Is this conversation helpful?", answer="boolean")


@loader(name="multi_item_model_usage_loader", messages=["user"])
def multi_item_model_usage_loader_factory() -> Loader[ChatMessageUser]:
    """Create a loader that makes one model call before yielding each message."""

    async def load(transcript: Transcript) -> AsyncIterator[ChatMessageUser]:
        for message in transcript.messages:
            if isinstance(message, ChatMessageUser):
                await get_model().generate([message])
                yield message

    return load


@scanner(
    name="multi_item_model_usage_scanner",
    loader=multi_item_model_usage_loader_factory(),
)
def multi_item_model_usage_scanner_factory() -> Scanner[ChatMessageUser]:
    """Create a scanner whose model usage occurs only inside its loader."""

    async def scan_message(message: ChatMessageUser) -> Result:
        return Result(value=bool(message.text))

    return scan_message


@loader(name="per_item_events_loader", messages=["user"])
def per_item_events_loader_factory() -> Loader[ChatMessageUser]:
    """Create a loader that makes one model call before yielding each message."""

    async def load(transcript: Transcript) -> AsyncIterator[ChatMessageUser]:
        for message in transcript.messages:
            if isinstance(message, ChatMessageUser):
                await get_model().generate([message])
                yield message

    return load


@scanner(name="per_item_events_scanner", loader=per_item_events_loader_factory())
def per_item_events_scanner_factory() -> Scanner[ChatMessageUser]:
    """Create a scanner that makes exactly one model call per loader item."""

    async def scan_message(message: ChatMessageUser) -> Result:
        await get_model().generate([message])
        return Result(value=message.text)

    return scan_message


@scanner(name="llm_dynamic_question_scanner", messages="all")
def llm_dynamic_question_scanner_factory() -> Scanner[Transcript]:
    """LLM scanner with dynamic question based on transcript."""

    async def dynamic_question(transcript: Transcript) -> str:
        num_messages = len(transcript.messages)
        return (
            f"In this {num_messages}-message conversation, was the assistant helpful?"
        )

    return llm_scanner(question=dynamic_question, answer="boolean")


@pytest.mark.parametrize("max_processes", [1, 2])
def test_scan_basic_e2e(max_processes: int) -> None:
    """Test basic scan functionality end-to-end with mock LLM."""
    # Configure mockllm to return properly formatted responses for llm_scanner
    # The llm_scanner expects responses ending with "ANSWER: yes" or "ANSWER: no"
    mock_responses = [
        ModelOutput.from_content(
            model="mockllm",
            content="The assistant in [M2] provided helpful information.\n\nANSWER: yes",
        ),
        ModelOutput.from_content(
            model="mockllm",
            content="The response in [M2] failed to address the user's question.\n\nANSWER: NO",
        ),
    ]

    # Run scan with both a simple scanner and an LLM scanner
    with tempfile.TemporaryDirectory() as tmpdir:
        status = scan(
            scanners=[simple_scanner_factory(), llm_scanner_factory()],
            transcripts=transcripts_from(LOGS_DIR),
            scans=tmpdir,
            limit=2,
            max_processes=max_processes,
            model="mockllm/model",
            model_args={"custom_outputs": mock_responses},
        )

        # Verify status
        assert status.complete
        assert status.location is not None

        # Verify simple scanner results
        results = scan_results_df(status.location, scanner="simple_scanner")
        simple_df = results.scanners["simple_scanner"]
        assert len(simple_df) == 2
        assert "value" in simple_df.columns
        assert "explanation" in simple_df.columns

        # Verify LLM scanner results
        results = scan_results_df(status.location, scanner="llm_test_scanner")
        llm_df = results.scanners["llm_test_scanner"]
        assert len(llm_df) == 2
        assert "value" in llm_df.columns
        assert "explanation" in llm_df.columns
        # Verify the LLM scanner parsed the responses correctly
        # In single-process mode, mock responses are consumed in order
        # In multi-process mode, each process gets its own copy starting at index 0
        if max_processes == 1:
            assert sorted(llm_df["value"].tolist()) == [False, True]
        else:
            assert all(isinstance(v, bool) for v in llm_df["value"].tolist())


@pytest.mark.parametrize("max_processes", [1, 2])
def test_scan_with_dynamic_question(max_processes: int) -> None:
    """Test LLM scanner with dynamic question callable."""
    # Configure mockllm to return properly formatted responses
    mock_responses = [
        ModelOutput.from_content(
            model="mockllm",
            content="Yes, the assistant was helpful.\n\nANSWER: yes",
        ),
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        status = scan(
            scanners=[llm_dynamic_question_scanner_factory()],
            transcripts=transcripts_from(LOGS_DIR),
            scans=tmpdir,
            limit=1,
            max_processes=max_processes,
            model="mockllm/model",
            model_args={"custom_outputs": mock_responses},
        )

        # Verify status
        assert status.complete
        assert status.location is not None

        # Verify dynamic question scanner results
        results = scan_results_df(
            status.location, scanner="llm_dynamic_question_scanner"
        )
        scanner_df = results.scanners["llm_dynamic_question_scanner"]
        assert len(scanner_df) == 1
        assert "value" in scanner_df.columns
        assert scanner_df["value"].tolist() == [True]


@scanner(name="count_scanner", messages="all")
def count_scanner_factory() -> Scanner[Transcript]:
    """Simple scanner that just counts transcripts for testing large batches."""

    async def scan_transcript(transcript: Transcript) -> Result:
        return Result(
            value=transcript.metadata.get("index", 0),
            explanation=f"Scanned {transcript.transcript_id}",
        )

    return scan_transcript


def test_scan_processes_all_transcripts_beyond_1000(tmp_path: Path) -> None:
    """Test that scans process ALL transcripts when count exceeds 1000.

    This is an end-to-end test that verifies no artificial limit of 1000
    is applied during scanning. It creates 1500 transcripts in a database,
    runs a scan without any limit, and verifies all 1500 are processed.
    """
    db_path = tmp_path / "transcript_db"
    scans_path = tmp_path / "scans"
    db_path.mkdir()
    scans_path.mkdir()

    # Create 1500 transcripts in the database (exceeds the batch_size=1000)
    transcript_count = 1500

    # Insert transcripts
    import asyncio

    async def insert_transcripts() -> None:
        transcripts = [
            create_minimal_transcript(f"test-{i:05d}", i)
            for i in range(transcript_count)
        ]
        async with transcripts_db(str(db_path)) as db:
            await db.insert(transcripts)

    asyncio.run(insert_transcripts())

    # Run scan WITHOUT any limit - should process all transcripts
    status = scan(
        scanners=[count_scanner_factory()],
        transcripts=transcripts_from(str(db_path)),
        scans=str(scans_path),
        max_processes=1,  # Single process for deterministic testing
        display="none",
    )

    # Verify scan completed
    assert status.complete, f"Scan did not complete: {status}"
    assert status.location is not None

    # Verify ALL transcripts were scanned
    results = scan_results_df(status.location, scanner="count_scanner")
    scanner_df = results.scanners["count_scanner"]

    assert len(scanner_df) == transcript_count, (
        f"Expected {transcript_count} scan results, got {len(scanner_df)}. "
        "This indicates a limit is being applied during scanning."
    )


def test_scan_with_scans_dir_under_logs_dir(tmp_path: Path) -> None:
    """Regression test for scans dir nested under the logs dir.

    When the scans output dir lives inside the logs dir, the parquet files
    written by the first scan get picked up by `_location_type`'s recursive
    glob on a subsequent scan, causing the logs dir to be misidentified as
    a transcript database. The second scan then "scans" the result parquets
    from the first scan instead of the actual eval logs.
    """
    logs_dir = tmp_path / "logs"
    shutil.copytree(LOGS_DIR, logs_dir)

    scans_dir = logs_dir / "scans"

    first_status = scan(
        scanners=[simple_scanner_factory()],
        transcripts=transcripts_from(str(logs_dir)),
        scans=str(scans_dir),
        limit=2,
        max_processes=1,
        display="none",
    )
    assert first_status.complete
    assert first_status.spec.transcripts is not None
    assert first_status.spec.transcripts.type == "eval_log"

    # Confirm the first scan wrote parquet files under the logs dir.
    assert list(scans_dir.rglob("*.parquet"))

    # The second scan must still treat logs_dir as eval logs, not a database.
    second_status = scan(
        scanners=[simple_scanner_factory()],
        transcripts=transcripts_from(str(logs_dir)),
        scans=str(scans_dir),
        limit=2,
        max_processes=1,
        display="none",
    )
    assert second_status.complete
    assert second_status.spec.transcripts is not None
    assert second_status.spec.transcripts.type == "eval_log", (
        "Second scan misclassified the logs dir as a transcript database "
        "because parquet files written by the first scan live underneath it."
    )


def test_scan_model_usage_not_cumulative(tmp_path: Path) -> None:
    """Test that scan_total_tokens reflects per-scan usage, not cumulative.

    Regression test for a bug where init_model_usage() didn't reset the
    model usage context between sequential scans within the same worker task,
    causing scan_total_tokens to accumulate across scans.
    """
    db_path = tmp_path / "transcript_db"
    scans_path = tmp_path / "scans"
    db_path.mkdir()
    scans_path.mkdir()

    transcript_count = 5

    import asyncio

    async def insert_transcripts() -> None:
        transcripts = [
            create_minimal_transcript(f"token-test-{i:03d}", i)
            for i in range(transcript_count)
        ]
        async with transcripts_db(str(db_path)) as db:
            await db.insert(transcripts)

    asyncio.run(insert_transcripts())

    mock_responses = [
        ModelOutput.from_content(
            model="mockllm",
            content="The assistant was helpful.\n\nANSWER: yes",
        )
        for _ in range(transcript_count)
    ]

    # max_transcripts=1 forces a single worker to process all scans
    # sequentially, which is where the cumulative bug manifests
    status = scan(
        scanners=[llm_scanner_factory()],
        transcripts=transcripts_from(str(db_path)),
        scans=str(scans_path),
        max_processes=1,
        max_transcripts=1,
        model="mockllm/model",
        model_args={"custom_outputs": mock_responses},
        display="none",
    )

    assert status.complete
    assert status.location is not None

    results = scan_results_df(
        status.location, scanner="llm_test_scanner", rows="transcripts"
    )
    df = results.scanners["llm_test_scanner"]
    assert len(df) == transcript_count

    # Every scan uses the same prompt/response, so each should report
    # identical token counts. Before the fix, tokens grew cumulatively:
    # [187, 374, 561, 748, 935] instead of [187, 187, 187, 187, 187].
    first_tokens = int(df["scan_total_tokens"].iloc[0])
    assert first_tokens > 0
    assert df["scan_total_tokens"].tolist() == [first_tokens] * transcript_count

    first_usage_str = df["scan_model_usage"].iloc[0]
    first_usage = json.loads(first_usage_str)
    model_name = next(iter(first_usage))
    assert first_usage[model_name]["input_tokens"] > 0
    assert first_usage[model_name]["output_tokens"] > 0
    assert first_usage[model_name]["total_tokens"] == first_tokens

    for i in range(1, transcript_count):
        usage = json.loads(df["scan_model_usage"].iloc[i])
        assert usage == first_usage, (
            f"scan_model_usage for scan {i} differs from scan 0: {usage} != {first_usage}"
        )


def test_scan_events_are_per_loader_item(tmp_path: Path) -> None:
    """Each report's events cover only its own item's invocation.

    Regression test for reports built from one Inspect transcript shared
    across every item a loader yields: item k recorded the events of items
    0..k, so the stored `scan_events` grew quadratically in the item count
    and attributed earlier items' model calls to later reports. The loader
    call that produces an item and the scan of that item both belong to
    that item's report.
    """
    db_path = tmp_path / "transcript_db"
    scans_path = tmp_path / "scans"
    db_path.mkdir()
    scans_path.mkdir()
    item_count = 5
    transcript = Transcript(
        transcript_id="per-item-events",
        source_type="test",
        source_id="source-0",
        source_uri="test://per-item-events",
        messages=[
            ChatMessageUser(content=f"Item {i} message") for i in range(item_count)
        ],
        events=[],
    )

    import asyncio

    async def insert_transcript() -> None:
        async with transcripts_db(str(db_path)) as db:
            await db.insert([transcript])

    asyncio.run(insert_transcript())
    status = scan(
        scanners=[per_item_events_scanner_factory()],
        transcripts=transcripts_from(str(db_path)),
        scans=str(scans_path),
        max_processes=1,
        model="mockllm/model",
        model_args={
            "custom_outputs": [
                ModelOutput.from_content(model="mockllm", content="ok")
                for _ in range(2 * item_count)
            ]
        },
        display="none",
    )
    assert status.complete
    assert status.location is not None
    # scan_events is a heavy column, excluded unless asked for
    df = scan_results_df(
        status.location, scanner="per_item_events_scanner", exclude_columns=[]
    ).scanners["per_item_events_scanner"]
    assert len(df) == item_count

    for i in range(item_count):
        events = json.loads(df["scan_events"].iloc[i])
        model_events = [e for e in events if e["event"] == "model"]
        # The loader's call for this item and the scan's call, and nothing
        # from items 0..i-1.
        assert len(model_events) == 2, (
            f"report {i} carries {len(model_events)} model events, expected 2"
        )
        for event in model_events:
            assert event["input"][0]["content"] == f"Item {i} message"
        # The scan span is recorded once per item alongside the calls.
        assert [e["event"] for e in events].count("span_begin") == 1


# Long enough to be condensed into an attachment, and shared by every call so
# later items reference an attachment first recorded for item 0.
SHARED_PROMPT = "Shared instructions for every item. " * 10


@loader(name="retained_transcript_loader", messages=["user"])
def retained_transcript_loader_factory() -> Loader[ChatMessageUser]:
    """Create a loader that logs each item through one saved transcript."""

    async def load(transcript: Transcript) -> AsyncIterator[ChatMessageUser]:
        log = inspect_transcript()
        for message in transcript.messages:
            if isinstance(message, ChatMessageUser):
                log.info(message.text)
                yield message

    return load


@loader(name="persistent_worker_loader", messages=["user"])
def persistent_worker_loader_factory(
    setup_span: bool = False, worker_span: bool = False, skip_first: bool = False
) -> Loader[list[ChatMessage]]:
    """Create a loader whose one worker task makes each item's model call.

    Args:
        setup_span: Start the worker inside a span that ends before the first
            yield, so the worker records under an ended span.
        worker_span: The worker records inside its own span, a child of
            wherever it started.
        skip_first: Yield an empty item, which gets no report, first.
    """

    async def load(transcript: Transcript) -> AsyncIterator[list[ChatMessage]]:
        requests: asyncio.Queue[ChatMessageUser | None] = asyncio.Queue()
        completed: asyncio.Queue[ChatMessageUser] = asyncio.Queue()
        started = asyncio.Event()

        async def worker() -> None:
            context: AbstractAsyncContextManager[None] = (
                span("worker") if worker_span else nullcontext()
            )
            async with context:
                started.set()
                while (message := await requests.get()) is not None:
                    await get_model().generate(
                        [ChatMessageUser(content=SHARED_PROMPT), message]
                    )
                    await completed.put(message)

        if setup_span:
            async with span("worker_setup"):
                worker_task = asyncio.create_task(worker())
        else:
            worker_task = asyncio.create_task(worker())
        try:
            await started.wait()
            if skip_first:
                yield []
            for message in transcript.messages:
                if isinstance(message, ChatMessageUser):
                    await requests.put(message)
                    yield [await completed.get()]
        finally:
            await requests.put(None)
            await worker_task

    return load


@loader(name="enclosing_span_loader", messages=["user"])
def enclosing_span_loader_factory() -> Loader[ChatMessageUser]:
    """Create a loader whose span stays open across every yield."""

    async def load(transcript: Transcript) -> AsyncIterator[ChatMessageUser]:
        async with span("loader"):
            for message in transcript.messages:
                if isinstance(message, ChatMessageUser):
                    inspect_transcript().info(message.text)
                    yield message

    return load


@loader(name="skipped_item_loader", messages=["user"])
def skipped_item_loader_factory() -> Loader[list[ChatMessage]]:
    """Create a loader that yields an empty item, which gets no report, first."""

    async def load(transcript: Transcript) -> AsyncIterator[list[ChatMessage]]:
        for message in transcript.messages:
            if isinstance(message, ChatMessageUser):
                inspect_transcript().info(f"skipped before {message.text}")
                yield []
                inspect_transcript().info(message.text)
                yield [message]

    return load


def _item_scanner(name: str, item_loader: Loader[Any]) -> Scanner[Any]:
    @scanner(name=name, loader=item_loader)
    def factory() -> Scanner[ChatMessage | list[ChatMessage]]:
        async def scan_item(item: ChatMessage | list[ChatMessage]) -> Result:
            return Result(value=True)

        return scan_item

    return factory()


class _LoaderCase(NamedTuple):
    factory: Callable[[], Loader[Any]]
    worker: bool = False
    """The loader's worker task makes one model call per item."""
    spans: tuple[str, ...] = ()
    """Loader spans every report must contain, besides its scan span."""


_LOADER_CASES = {
    "retained_transcript_loader": _LoaderCase(retained_transcript_loader_factory),
    "persistent_worker_loader": _LoaderCase(
        persistent_worker_loader_factory, worker=True
    ),
    "worker_in_ended_span": _LoaderCase(
        lambda: persistent_worker_loader_factory(setup_span=True),
        worker=True,
        spans=("worker_setup",),
    ),
    "worker_child_of_ended_span": _LoaderCase(
        lambda: persistent_worker_loader_factory(setup_span=True, worker_span=True),
        worker=True,
        spans=("worker_setup", "worker"),
    ),
    "worker_in_ended_span_skipped_first": _LoaderCase(
        lambda: persistent_worker_loader_factory(setup_span=True, skip_first=True),
        worker=True,
        spans=("worker_setup",),
    ),
    "worker_child_of_ended_span_skipped_first": _LoaderCase(
        lambda: persistent_worker_loader_factory(
            setup_span=True, worker_span=True, skip_first=True
        ),
        worker=True,
        spans=("worker_setup", "worker"),
    ),
    "enclosing_span_loader": _LoaderCase(
        enclosing_span_loader_factory, spans=("loader",)
    ),
    "skipped_item_loader": _LoaderCase(skipped_item_loader_factory),
}


def _dangling_span_refs(events: list[dict[str, Any]]) -> list[str]:
    """Span ids referenced by `events` whose `span_begin` is not among them."""
    begun = {e["id"] for e in events if e["event"] == "span_begin"}
    refs = [e.get("span_id") for e in events]
    refs += [e.get("parent_id") for e in events if e["event"] == "span_begin"]
    refs += [e["id"] for e in events if e["event"] == "span_end"]
    return [ref for ref in refs if ref is not None and ref not in begun]


@pytest.mark.parametrize(
    "loader_name",
    [
        pytest.param(
            name,
            marks=pytest.mark.skipif(
                case.worker
                and os.environ.get("INSPECT_ASYNC_BACKEND", "").lower() == "trio",
                reason="the worker is an asyncio task",
            ),
        )
        for name, case in _LOADER_CASES.items()
    ],
)
def test_scan_events_survive_loader_state_across_yields(
    tmp_path: Path, loader_name: str
) -> None:
    """Loader state that outlives a yield still records into each item's report.

    A saved `transcript()` reference, a worker task started before the first
    yield, and a span open across yields all keep the transcript they were
    created with; replacing the transcript per item lost their later events
    or left later reports with dangling span references. A worker keeps
    recording under the span it started in after that span ends, so later
    reports still need that span's begin event. Events recorded for an empty
    item, which gets no report, stay out of the next item's report.
    """
    case = _LOADER_CASES[loader_name]
    db_path = tmp_path / "transcript_db"
    scans_path = tmp_path / "scans"
    db_path.mkdir()
    scans_path.mkdir()
    item_count = 3
    transcript = Transcript(
        transcript_id=f"{loader_name}-events",
        source_type="test",
        source_id="source-0",
        source_uri=f"test://{loader_name}-events",
        messages=[
            ChatMessageUser(content=f"Item {i} message") for i in range(item_count)
        ],
        events=[],
    )

    async def insert_transcript() -> None:
        async with transcripts_db(str(db_path)) as db:
            await db.insert([transcript])

    asyncio.run(insert_transcript())
    scanner_name = f"{loader_name}_scanner"
    status = scan(
        scanners=[_item_scanner(scanner_name, case.factory())],
        transcripts=transcripts_from(str(db_path)),
        scans=str(scans_path),
        max_processes=1,
        model="mockllm/model",
        display="none",
    )
    assert status.complete
    assert status.location is not None
    df = scan_results_df(
        status.location, scanner=scanner_name, exclude_columns=[]
    ).scanners[scanner_name]
    assert len(df) == item_count

    for i in range(item_count):
        events: list[dict[str, Any]] = json.loads(df["scan_events"].iloc[i])
        item_text = f"Item {i} message"
        assert _dangling_span_refs(events) == [], f"report {i}"
        span_names = [e["name"] for e in events if e["event"] == "span_begin"]
        # Earlier items' completed scan spans stay in their own reports.
        assert span_names.count("scan") == 1, f"report {i}: {span_names}"
        if case.worker:
            model_events = [e for e in events if e["event"] == "model"]
            assert [e["input"][-1]["content"] for e in model_events] == [item_text]
            # Attachments resolve for every report, including ones first
            # recorded while producing an earlier item.
            call = json.dumps(model_events[0]["call"])
            assert "attachment://" not in call
            assert SHARED_PROMPT in call
        else:
            infos = [e["data"] for e in events if e["event"] == "info"]
            assert infos == [item_text], f"report {i}"
        for name in case.spans:
            assert name in span_names, f"report {i}: {span_names}"


def test_scan_model_usage_is_per_loader_item(tmp_path: Path) -> None:
    """Each report includes the loader call made immediately before its item."""
    db_path = tmp_path / "transcript_db"
    scans_path = tmp_path / "scans"
    db_path.mkdir()
    scans_path.mkdir()
    transcript = Transcript(
        transcript_id="loader-model-usage",
        source_type="test",
        source_id="source-0",
        source_uri="test://loader-model-usage",
        messages=[
            ChatMessageUser(content="First message"),
            ChatMessageUser(content="Second message"),
            ChatMessageUser(content="Third message"),
        ],
        events=[],
    )

    import asyncio

    async def insert_transcript() -> None:
        async with transcripts_db(str(db_path)) as db:
            await db.insert([transcript])

    asyncio.run(insert_transcript())
    status = scan(
        scanners=[multi_item_model_usage_scanner_factory()],
        transcripts=transcripts_from(str(db_path)),
        scans=str(scans_path),
        max_processes=1,
        model="mockllm/model",
        model_args={
            "custom_outputs": [
                ModelOutput.from_content(model="mockllm", content="ok")
                for _ in range(3)
            ]
        },
        display="none",
    )
    assert status.complete
    assert status.location is not None
    df = scan_results_df(
        status.location, scanner="multi_item_model_usage_scanner"
    ).scanners["multi_item_model_usage_scanner"]
    first_tokens = int(df["scan_total_tokens"].iloc[0])
    assert first_tokens > 0
    assert df["scan_total_tokens"].tolist() == [first_tokens] * 3
    assert status.summary.scanners["multi_item_model_usage_scanner"].tokens == (
        3 * first_tokens
    )
