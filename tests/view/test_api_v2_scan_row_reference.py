"""Reference-mode rows through GET /scans/{dir}/{scan}/{scanner}/{uuid}."""

import base64
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import pyarrow.parquet as pq
import pytest
from fastapi.testclient import TestClient
from inspect_scout import Result, Scanner, scan, scanner
from inspect_scout._transcript.factory import transcripts_from
from inspect_scout._transcript.reference import (
    InputReference,
    InputReferenceUnavailable,
)
from inspect_scout._transcript.types import Transcript
from inspect_scout._view._api_v2 import v2_api_app
from inspect_scout._view._input_reference import source_uri_locator
from starlette.requests import Request

LOGS = (
    Path(__file__).parent.parent
    / "recorder"
    / "logs"
    / "2025-11-07T10-59-47-05-00_websearch-addition-problem_LqPDntDnkk4h2fSqQ8i6CE.eval"
)
COLUMNS = ["input", "input_type", "input_data", "input_storage", "scan_events"]


@dataclass(frozen=True)
class ScanRow:
    scan_dir: Path
    scanner: str
    uuid: str

    def url(self, columns: list[str] = COLUMNS) -> str:
        def b64(s: str) -> str:
            return base64.urlsafe_b64encode(s.encode()).decode().rstrip("=")

        query = "&".join(f"column={c}" for c in columns)
        return (
            f"/scans/{b64(str(self.scan_dir.parent))}/{b64(self.scan_dir.name)}"
            f"/{self.scanner}/{self.uuid}?{query}"
        )

    @property
    def parquet(self) -> Path:
        return self.scan_dir / f"{self.scanner}.parquet"


@scanner(messages="all")
def probe() -> Scanner[Transcript]:
    async def scan_fn(transcript: Transcript) -> Result:
        return Result(value=len(transcript.messages))

    return scan_fn


def _scan(scans: Path, record_input: Literal["copy", "reference"]) -> ScanRow:
    status = scan(
        scanners=[probe()],
        transcripts=transcripts_from(LOGS),
        scans=str(scans),
        max_processes=1,
        record_input=record_input,
        display="none",
    )
    assert status.complete and status.location
    scan_dir = Path(status.location)
    uuid = pq.read_table(
        scan_dir / "probe.parquet", columns=["uuid"], partitioning=None
    )["uuid"][0]
    return ScanRow(scan_dir, "probe", uuid.as_py())


@pytest.fixture(scope="module")
def reference_row(tmp_path_factory: pytest.TempPathFactory) -> ScanRow:
    return _scan(tmp_path_factory.mktemp("scans"), "reference")


@pytest.fixture(scope="module")
def legacy_inline_row(tmp_path_factory: pytest.TempPathFactory) -> ScanRow:
    """A copy-mode row in a parquet written before the reference columns existed."""
    row = _scan(tmp_path_factory.mktemp("scans"), "copy")
    table = pq.read_table(row.parquet, partitioning=None)
    pq.write_table(table.drop_columns(["input_storage", "input_content"]), row.parquet)
    return row


def _get(client: TestClient, url: str) -> dict[str, Any]:
    response = client.get(url)
    assert response.status_code == 200
    body: dict[str, Any] = response.json()
    return body


def test_reference_row_resolves(reference_row: ScanRow) -> None:
    client = TestClient(v2_api_app(input_reference_locator=source_uri_locator))

    body = _get(client, reference_row.url())

    assert set(body) == set(COLUMNS)
    assert body["input_storage"] == "reference"
    assert body["input_type"] == "transcript"
    assert len(body["input"]["messages"]) == 2
    assert body["input"]["events"] == []
    assert body["input_data"] == {"messages": [], "calls": []}
    assert body["scan_events"] is not None


def test_resolves_only_the_requested_columns(reference_row: ScanRow) -> None:
    client = TestClient(v2_api_app(input_reference_locator=source_uri_locator))

    body = _get(client, reference_row.url(["input"]))

    assert set(body) == {"input"}
    assert len(body["input"]["messages"]) == 2


def test_reference_row_is_not_resolved_by_default(reference_row: ScanRow) -> None:
    body = _get(TestClient(v2_api_app()), reference_row.url())

    assert body["input"] is None
    assert body["input_data"] is None
    assert body["input_storage"] == "reference"
    assert body["scan_events"] is not None
    assert body["input_error"] == {
        "reason": "not_resolved",
        "message": "This result's input is stored by reference, and this server "
        "does not resolve references.",
    }


def test_resolution_failure_keeps_the_row(reference_row: ScanRow) -> None:
    async def forbid(request: Request, ref: InputReference) -> str:
        raise InputReferenceUnavailable("forbidden", "You can't see this sample.")

    body = _get(
        TestClient(v2_api_app(input_reference_locator=forbid)), reference_row.url()
    )

    assert body["input"] is None
    assert body["scan_events"] is not None
    assert body["input_error"] == {
        "reason": "forbidden",
        "message": "You can't see this sample.",
    }


def test_legacy_parquet_is_inline(legacy_inline_row: ScanRow) -> None:
    # No resolver: a legacy row misread as a reference would come back null
    # with `input_error` instead of being silently re-read from its source.
    client = TestClient(v2_api_app())

    body = _get(client, legacy_inline_row.url())

    assert "input_error" not in body
    assert body["input_storage"] is None
    assert len(body["input"]["messages"]) == 2
