"""Tests for the /project/config endpoints."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from inspect_scout._view._api_v2 import v2_api_app
from ruamel.yaml import YAML
from starlette.status import HTTP_200_OK, HTTP_412_PRECONDITION_FAILED

SCOUT_YAML = """\
# my project
name: my-project
transcripts: ./logs
filter: "task_set = 'x'"
model: openai/gpt-5
model_roles:
  grader: anthropic/claude-x
scanners:
  - name: refusal
    file: scanners.py
worklist:
  - scanner: refusal
    transcripts: [t1]
validation:
  refusal: validation.csv
results_buffer: 100
max_transcripts: 10
"""

EDITABLE_KEYS = {
    "transcripts",
    "filter",
    "scans",
    "max_transcripts",
    "max_processes",
    "limit",
    "shuffle",
    "tags",
    "metadata",
    "log_level",
    "model",
    "model_base_url",
    "model_args",
    "generate_config",
}


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "scout.yaml").write_text(SCOUT_YAML, encoding="utf-8")
    return TestClient(v2_api_app())


def test_put_keeps_keys_the_settings_page_does_not_send(
    client: TestClient, tmp_path: Path
) -> None:
    current = client.get("/project/config")

    # The settings page's payload after changing only Max Transcripts: the
    # non-null values GET returned for the keys it has controls for.
    payload = {
        key: value
        for key, value in current.json().items()
        if key in EDITABLE_KEYS and value is not None
    }
    payload["max_transcripts"] = 20
    response = client.put(
        "/project/config",
        json=payload,
        headers={"If-Match": current.headers["ETag"]},
    )

    assert response.status_code == HTTP_200_OK
    body = response.json()
    assert body["max_transcripts"] == 20
    assert body["name"] == "my-project"
    content = (tmp_path / "scout.yaml").read_text(encoding="utf-8")
    assert content.startswith("# my project\n")
    assert YAML(typ="safe").load(content) == {
        "name": "my-project",
        "transcripts": "./logs",
        "filter": "task_set = 'x'",
        "model": "openai/gpt-5",
        "model_roles": {"grader": "anthropic/claude-x"},
        "scanners": [{"name": "refusal", "file": "scanners.py"}],
        "worklist": [{"scanner": "refusal", "transcripts": ["t1"]}],
        "validation": {"refusal": "validation.csv"},
        "results_buffer": 100,
        "max_transcripts": 20,
    }


def test_put_with_stale_etag_is_rejected(client: TestClient) -> None:
    response = client.put(
        "/project/config",
        json={"filter": "task_set = 'x'", "max_transcripts": 20},
        headers={"If-Match": '"stale"'},
    )
    assert response.status_code == HTTP_412_PRECONDITION_FAILED
