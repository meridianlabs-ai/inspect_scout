"""Tests for saving project configuration (write_project_config)."""

import copy
from pathlib import Path
from typing import Any

import pytest
from inspect_scout._project._project import (
    EtagMismatchError,
    compute_project_etag,
    write_project_config,
)
from inspect_scout._project.types import ProjectConfig
from ruamel.yaml import YAML

BASE_YAML = """\
# my project
name: my-project  # display name
transcripts: ./logs
filter: "task_set = 'x'"
scans: ./scans
model: openai/gpt-5
model_roles:
  grader: anthropic/claude-x
scanners:
  - name: refusal
    file: scanners.py
worklist:
  - scanner: refusal
    transcripts: [t1, t2]
validation:
  refusal: validation.csv
results_buffer: 100
max_transcripts: 10
tags: [a, b]
metadata:
  team: evals  # owner
  cost_center: 42
generate_config:
  temperature: 0.5  # sampling
  max_tokens: 1000
  cache:
    expiry: 1W
    per_epoch: false
"""

BASE: dict[str, Any] = {
    "name": "my-project",
    "transcripts": "./logs",
    "filter": "task_set = 'x'",
    "scans": "./scans",
    "model": "openai/gpt-5",
    "model_roles": {"grader": "anthropic/claude-x"},
    "scanners": [{"name": "refusal", "file": "scanners.py"}],
    "worklist": [{"scanner": "refusal", "transcripts": ["t1", "t2"]}],
    "validation": {"refusal": "validation.csv"},
    "results_buffer": 100,
    "max_transcripts": 10,
    "tags": ["a", "b"],
    "metadata": {"team": "evals", "cost_center": 42},
    "generate_config": {
        "temperature": 0.5,
        "max_tokens": 1000,
        "cache": {"expiry": "1W", "per_epoch": False},
    },
}

# What the settings page sends for BASE when nothing was edited: the non-empty
# values of the keys it has controls for.
FRONTEND_UNCHANGED: dict[str, Any] = {
    key: BASE[key]
    for key in (
        "transcripts",
        "filter",
        "scans",
        "model",
        "max_transcripts",
        "tags",
        "metadata",
        "generate_config",
    )
}

REMOVED = object()


def _load(path: Path) -> Any:
    return YAML(typ="safe").load(path.read_text(encoding="utf-8"))


def _expected(changes: dict[str, Any]) -> dict[str, Any]:
    expected = copy.deepcopy(BASE)
    for key, value in changes.items():
        if value is REMOVED:
            del expected[key]
        else:
            expected[key] = value
    return expected


def _save(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, payload: dict[str, Any]
) -> Path:
    monkeypatch.chdir(tmp_path)
    project_file = tmp_path / "scout.yaml"
    project_file.write_text(BASE_YAML, encoding="utf-8")
    write_project_config(ProjectConfig.model_validate(payload), None)
    return project_file


@pytest.mark.parametrize(
    ("payload", "changes"),
    [
        pytest.param(FRONTEND_UNCHANGED, {}, id="unchanged-save"),
        pytest.param({"filter": BASE["filter"]}, {}, id="minimal-payload"),
        pytest.param(
            {**FRONTEND_UNCHANGED, "max_transcripts": 20},
            {"max_transcripts": 20},
            id="update-scalar",
        ),
        pytest.param(
            {**FRONTEND_UNCHANGED, "limit": 5, "model_args": {"k": 1}},
            {"limit": 5, "model_args": {"k": 1}},
            id="add-new-keys",
        ),
        # The settings page clears a top-level field by sending null.
        pytest.param(
            {**FRONTEND_UNCHANGED, "model": None},
            {"model": REMOVED},
            id="clear-text-field",
        ),
        pytest.param(
            {**FRONTEND_UNCHANGED, "max_transcripts": None},
            {"max_transcripts": REMOVED},
            id="clear-number-field",
        ),
        pytest.param(
            {**FRONTEND_UNCHANGED, "tags": None},
            {"tags": REMOVED},
            id="clear-tags",
        ),
        pytest.param(
            {**FRONTEND_UNCHANGED, "metadata": None},
            {"metadata": REMOVED},
            id="clear-metadata",
        ),
        pytest.param(
            {**FRONTEND_UNCHANGED, "generate_config": None},
            {"generate_config": REMOVED},
            id="clear-generate-config",
        ),
        pytest.param(
            {**FRONTEND_UNCHANGED, "tags": []},
            {"tags": REMOVED},
            id="empty-list-clears",
        ),
        pytest.param(
            {**FRONTEND_UNCHANGED, "metadata": {}},
            {"metadata": REMOVED},
            id="empty-dict-clears",
        ),
        pytest.param(
            {**FRONTEND_UNCHANGED, "name": None, "validation": None},
            {"name": REMOVED, "validation": REMOVED},
            id="explicit-null-clears-uneditable-key",
        ),
        # A present nested value replaces the original as a whole: the page
        # sends the full edited dict, and a sub-key it leaves out is one the
        # user removed.
        pytest.param(
            {**FRONTEND_UNCHANGED, "metadata": {"team": "evals"}},
            {"metadata": {"team": "evals"}},
            id="metadata-key-removed",
        ),
        pytest.param(
            {
                **FRONTEND_UNCHANGED,
                "generate_config": {
                    "max_tokens": 1000,
                    "cache": {"expiry": "1W", "per_epoch": False},
                },
            },
            {
                "generate_config": {
                    "max_tokens": 1000,
                    "cache": {"expiry": "1W", "per_epoch": False},
                }
            },
            id="generate-config-field-cleared",
        ),
        pytest.param(
            {
                **FRONTEND_UNCHANGED,
                "generate_config": {"temperature": 0.5, "max_tokens": 1000},
            },
            {"generate_config": {"temperature": 0.5, "max_tokens": 1000}},
            id="cache-disabled",
        ),
        pytest.param(
            {
                **FRONTEND_UNCHANGED,
                "generate_config": {
                    "temperature": 0.5,
                    "max_tokens": 1000,
                    "cache": {"expiry": None, "per_epoch": False},
                },
            },
            {
                "generate_config": {
                    "temperature": 0.5,
                    "max_tokens": 1000,
                    "cache": {"per_epoch": False},
                }
            },
            id="cache-sub-field-cleared",
        ),
    ],
)
def test_save_applies_payload_as_top_level_patch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    payload: dict[str, Any],
    changes: dict[str, Any],
) -> None:
    project_file = _save(tmp_path, monkeypatch, payload)
    assert _load(project_file) == _expected(changes)


def test_save_preserves_comments(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project_file = _save(
        tmp_path, monkeypatch, {**FRONTEND_UNCHANGED, "max_transcripts": 20}
    )
    content = project_file.read_text(encoding="utf-8")
    for comment in ("# my project", "# display name", "# owner", "# sampling"):
        assert comment in content


@pytest.mark.parametrize(
    ("payload", "expected_scans"),
    [
        pytest.param({"filter": [], "scans": "./old"}, "./old", id="scans-kept"),
        pytest.param({"filter": [], "scans": "./new"}, "./new", id="scans-changed"),
        pytest.param({"filter": [], "scans": None}, None, id="scans-cleared"),
        pytest.param({"filter": []}, "./old", id="scans-omitted"),
    ],
)
def test_save_with_deprecated_results_key(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    payload: dict[str, Any],
    expected_scans: str | None,
) -> None:
    monkeypatch.chdir(tmp_path)
    project_file = tmp_path / "scout.yaml"
    project_file.write_text("results: ./old\n", encoding="utf-8")

    updated, _ = write_project_config(ProjectConfig.model_validate(payload), None)

    assert updated.scans == expected_scans
    data = _load(project_file) or {}
    assert ("results" in data) == ("scans" not in payload)


def test_save_creates_new_file_with_set_fields_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    write_project_config(
        ProjectConfig.model_validate(
            {"filter": [], "model": "openai/gpt-5", "limit": None}
        ),
        None,
    )
    assert _load(tmp_path / "scout.yaml") == {"model": "openai/gpt-5"}


def test_save_checks_etag(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    project_file = tmp_path / "scout.yaml"
    project_file.write_text(BASE_YAML, encoding="utf-8")

    with pytest.raises(EtagMismatchError):
        write_project_config(
            ProjectConfig.model_validate({"filter": [], "max_transcripts": 20}),
            "stale",
        )

    _, etag = write_project_config(
        ProjectConfig.model_validate({"filter": [], "max_transcripts": 20}),
        compute_project_etag(BASE_YAML),
    )
    assert etag == compute_project_etag(project_file.read_text(encoding="utf-8"))
