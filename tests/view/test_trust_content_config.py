"""Tests for the viewer-wide trust_content cap."""

from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner
from fastapi.testclient import TestClient
from inspect_ai._util.error import PrerequisiteError
from inspect_scout._cli.main import scout
from inspect_scout._project import load_project_config
from inspect_scout._view._api_v2 import v2_api_app
from inspect_scout._view.types import ViewConfig


def _write(path: Path, trust_content: bool | None) -> None:
    lines = ["transcripts: ./logs"]
    if trust_content is not None:
        lines.append(f"trust_content: {str(trust_content).lower()}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


@pytest.mark.parametrize(
    ("cli", "project", "local", "expected"),
    [
        (None, None, None, None),
        (True, None, None, None),
        (False, None, None, False),
        (None, True, None, None),
        (None, False, None, False),
        # --trust-content can't raise what the project lowered
        (True, False, None, False),
        (False, True, None, False),
        # scout.local.yaml can lower trust but never raise it
        (None, None, False, False),
        (None, False, True, False),
        (None, True, False, False),
        (True, True, True, None),
    ],
)
def test_app_config_trust_content_is_the_lowest_setting(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    cli: bool | None,
    project: bool | None,
    local: bool | None,
    expected: bool | None,
) -> None:
    monkeypatch.chdir(tmp_path)
    _write(tmp_path / "scout.yaml", project)
    if local is not None:
        _write(tmp_path / "scout.local.yaml", local)

    client = TestClient(v2_api_app(view_config=ViewConfig(trust_content_cli=cli)))
    response = client.get("/app-config")

    assert response.status_code == 200
    assert response.json()["trust_content"] == expected


def test_app_config_reflects_project_changes_without_restart(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    _write(tmp_path / "scout.yaml", None)
    client = TestClient(v2_api_app())
    assert client.get("/app-config").json()["trust_content"] is None

    _write(tmp_path / "scout.yaml", False)
    assert client.get("/app-config").json()["trust_content"] is False


def test_project_rejects_non_boolean_trust_content(tmp_path: Path) -> None:
    project_file = tmp_path / "scout.yaml"
    project_file.write_text("trust_content: maybe\n", encoding="utf-8")

    with pytest.raises(PrerequisiteError, match="trust_content|maybe"):
        load_project_config(project_file)


@pytest.mark.parametrize(
    ("args", "env", "expected"),
    [
        ([], None, None),
        (["--no-trust-content"], None, False),
        (["--trust-content"], None, True),
        ([], "false", False),
        ([], "true", True),
        # the command line wins over the environment
        (["--trust-content"], "false", True),
    ],
)
def test_view_command_trust_content(
    monkeypatch: pytest.MonkeyPatch,
    args: list[str],
    env: str | None,
    expected: bool | None,
) -> None:
    captured: dict[str, Any] = {}

    def fake_view(**kwargs: Any) -> None:
        captured.update(kwargs)

    monkeypatch.setattr("inspect_scout._cli.view.view", fake_view)
    monkeypatch.delenv("SCOUT_VIEW_TRUST_CONTENT", raising=False)
    if env is not None:
        monkeypatch.setenv("SCOUT_VIEW_TRUST_CONTENT", env)

    result = CliRunner().invoke(scout, ["view", *args])

    assert result.exit_code == 0, result.output
    assert captured["trust_content"] is expected


def test_view_command_rejects_invalid_trust_content_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("inspect_scout._cli.view.view", lambda **_: None)
    monkeypatch.setenv("SCOUT_VIEW_TRUST_CONTENT", "maybe")

    result = CliRunner().invoke(scout, ["view"])

    assert result.exit_code != 0
