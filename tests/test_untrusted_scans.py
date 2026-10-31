"""Reading scan results someone else wrote must not run code the scan names.

A scan's `_scan.json` names source files (each scanner's `file`, the scan
job's `scan_file`, a registered validation predicate's `file`), registry
parameters that can describe a model, and the scan's model and model roles.
Listing, status, results and the viewer API read those fields as data: they
never import a named file and never construct a model. `scan_resume()` is a
run operation and does both; the last test pins that, which also proves the
fixture's references are live.

A marker module records each import of it in a file, and a spy on
`ModelAPI.__init__` records providers built with the fixture's base URL.
"""

import base64
import json
from pathlib import Path
from typing import Any, Callable

import pytest
from fastapi.testclient import TestClient
from inspect_ai.model._model import ModelAPI
from inspect_scout import (
    Result,
    Scanner,
    Transcript,
    ValidationPredicate,
    scan,
    scan_complete,
    scan_list,
    scan_results_arrow,
    scan_results_df,
    scan_resume,
    scan_status,
    scanner,
    transcripts_from,
    validation_predicate,
)
from inspect_scout._scanresults import scan_results_db
from inspect_scout._view._api_v2 import v2_api_app
from pydantic import JsonValue

LOGS_DIR = Path(__file__).parent / "recorder" / "logs"
SCANNER = "untrusted_scan_scanner"
PREDICATE = "untrusted_scan_predicate"
UNTRUSTED_URL = "https://untrusted.invalid/v1"
MODEL_CONFIG = {
    "model": "mockllm/model",
    "config": {},
    "base_url": UNTRUSTED_URL,
    "args": {},
}
# The shape registry_kwargs() turns into get_model(...).
MODEL_DICT = {
    "model": "mockllm/model",
    "config": {},
    "base_url": UNTRUSTED_URL,
    "model_args": {},
}

scanner_calls: list[str] = []


@scanner(name=SCANNER, messages="all")
def untrusted_scan_scanner(option: Any = None) -> Scanner[Transcript]:
    async def scan_transcript(transcript: Transcript) -> Result:
        scanner_calls.append(transcript.transcript_id)
        if len(scanner_calls) == 1:
            raise RuntimeError("first transcript fails so the scan is incomplete")
        return Result(value=True)

    return scan_transcript


@validation_predicate(name=PREDICATE)
def untrusted_scan_predicate(option: Any = None) -> ValidationPredicate:
    async def check(result: Result, target: JsonValue) -> bool:
        return result.value == target

    return check


def _marker_source(imports: Path) -> str:
    return f"with open({str(imports)!r}, 'a') as f:\n    f.write(__file__ + '\\n')\n"


def _imported(imports: Path) -> list[str]:
    return imports.read_text().splitlines() if imports.exists() else []


class UntrustedScan:
    def __init__(self, tmp_path: Path) -> None:
        self.imports = tmp_path / "imports.txt"
        self.scanner_file = tmp_path / "scanner_marker.py"
        self.scanjob_file = tmp_path / "scanjob_marker.py"
        self.predicate_file = tmp_path / "predicate_marker.py"
        for path in (self.scanner_file, self.scanjob_file, self.predicate_file):
            path.write_text(_marker_source(self.imports))
        self.scans_dir = tmp_path / "scans"
        self.location = ""

    def imported(self) -> list[str]:
        return _imported(self.imports)


@pytest.fixture
def untrusted_scan(tmp_path: Path) -> UntrustedScan:
    """An incomplete scan whose spec names marker files and a hostile model."""
    scanner_calls.clear()
    fixture = UntrustedScan(tmp_path)
    status = scan(
        scanners=[untrusted_scan_scanner()],
        transcripts=transcripts_from(LOGS_DIR),
        scans=fixture.scans_dir.as_posix(),
        limit=3,
        max_processes=1,
        display="none",
    )
    assert not status.complete
    fixture.location = status.location

    spec_path = Path(status.location) / "_scan.json"
    spec = json.loads(spec_path.read_text())
    spec["scan_file"] = fixture.scanjob_file.as_posix()
    spec["scan_args"] = {"option": MODEL_DICT}
    spec["scanners"][SCANNER].update(
        file=fixture.scanner_file.as_posix(), params={"option": MODEL_DICT}
    )
    spec["model"] = MODEL_CONFIG
    spec["model_roles"] = {"grader": MODEL_CONFIG}
    spec["validation"] = {
        SCANNER: {
            "cases": [{"id": "id-1", "target": True}],
            "predicate": {
                "kind": "registered",
                "name": PREDICATE,
                "args": {"option": MODEL_DICT},
                "file": fixture.predicate_file.as_posix(),
            },
        }
    }
    spec_path.write_text(json.dumps(spec))
    scanner_calls.clear()
    return fixture


@pytest.fixture
def untrusted_models(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Spy on model provider construction: providers built with UNTRUSTED_URL."""
    built: list[str] = []
    real_init = ModelAPI.__init__

    def spy(self: ModelAPI, *args: Any, **kwargs: Any) -> None:
        base_url = args[1] if len(args) > 1 else kwargs.get("base_url")
        if base_url == UNTRUSTED_URL:
            built.append(base_url)
        real_init(self, *args, **kwargs)

    monkeypatch.setattr(ModelAPI, "__init__", spy)
    return built


def _b64(value: str) -> str:
    return base64.urlsafe_b64encode(value.encode()).decode().rstrip("=")


def _view_requests(fixture: UntrustedScan) -> None:
    scans_dir = _b64(fixture.scans_dir.as_posix())
    scan_rel = _b64(Path(fixture.location).name)
    df = scan_results_df(fixture.location, scanner=SCANNER).scanners[SCANNER]
    uuid = str(df["uuid"].dropna().iloc[0])
    with TestClient(v2_api_app()) as client:
        for response in (
            client.post(f"/scans/{scans_dir}", json={}),
            client.get(f"/scans/{scans_dir}/{scan_rel}"),
            client.get(
                f"/scans/{scans_dir}/{scan_rel}",
                headers={"accept": "application/zip"},
            ),
            client.get(f"/scans/{scans_dir}/{scan_rel}/{SCANNER}"),
            client.get(
                f"/scans/{scans_dir}/{scan_rel}/{SCANNER}/{uuid}",
                params={"column": "value"},
            ),
        ):
            assert response.status_code == 200, response.text


def _arrow(fixture: UntrustedScan) -> None:
    with scan_results_arrow(fixture.location).reader(SCANNER) as reader:
        reader.read_all()


def _db(fixture: UntrustedScan) -> None:
    with scan_results_db(fixture.location) as db:
        db.conn.execute(f'SELECT * FROM "{SCANNER}"').fetchall()


READ_OPERATIONS: dict[str, Callable[[UntrustedScan], object]] = {
    "scan_status": lambda f: scan_status(f.location),
    "scan_list": lambda f: scan_list(f.scans_dir.as_posix()),
    "scan_results_df": lambda f: scan_results_df(f.location),
    "scan_results_df_transcripts": lambda f: scan_results_df(
        f.location, rows="transcripts"
    ),
    "scan_results_arrow": _arrow,
    "scan_results_db": _db,
    "scan_complete": lambda f: scan_complete(f.location, display="none"),
    "view_api": _view_requests,
}


@pytest.mark.parametrize("operation", READ_OPERATIONS.values(), ids=READ_OPERATIONS)
def test_read_operations_do_not_run_scan_code(
    operation: Callable[[UntrustedScan], object],
    untrusted_scan: UntrustedScan,
    untrusted_models: list[str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    cache = tmp_path / "cache"
    monkeypatch.setattr(
        "inspect_scout._scanjobs.cache_path.scout_cache_dir",
        lambda subdir=None: cache / subdir if subdir else cache,
    )

    operation(untrusted_scan)

    assert untrusted_scan.imported() == []
    assert untrusted_models == []
    assert scanner_calls == []


def test_resume_runs_code_the_scan_names(
    untrusted_scan: UntrustedScan, untrusted_models: list[str]
) -> None:
    scan_resume(untrusted_scan.location, display="none")

    assert sorted(untrusted_scan.imported()) == sorted(
        [
            untrusted_scan.scanner_file.as_posix(),
            untrusted_scan.predicate_file.as_posix(),
        ]
    )
    assert untrusted_models
    assert scanner_calls
