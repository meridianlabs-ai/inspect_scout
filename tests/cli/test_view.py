from __future__ import annotations

from typing import Any

import click
import inspect_scout._cli.view as view_cli
import pytest
from click.testing import CliRunner
from inspect_scout._view.network import ViewerNetworkPolicyError


def test_view_network_options_are_forwarded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def fake_view(**kwargs: Any) -> None:
        captured.update(kwargs)

    monkeypatch.setattr(view_cli, "view", fake_view)
    monkeypatch.setattr(view_cli, "process_common_options", lambda _options: None)
    monkeypatch.setattr(view_cli, "resolve_view_authorization", lambda: None)

    result = CliRunner().invoke(
        view_cli.view_command,
        [
            "--trusted-origin",
            "http://my-scout:7576",
            "--trusted-origin",
            "https://scout.example",
            "--trusted-host",
            "health.internal:7576",
            "--unsafe-allow-unauthenticated",
            "--root-path",
            "/proxy",
        ],
        standalone_mode=False,
    )

    assert result.exit_code == 0, result.output
    assert captured["trusted_origins"] == (
        "http://my-scout:7576",
        "https://scout.example",
    )
    assert captured["trusted_hosts"] == ("health.internal:7576",)
    assert captured["unsafe_allow_unauthenticated"] is True
    assert captured["root_path"] == "/proxy"


def test_view_authorization_is_forwarded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def fake_view(**kwargs: Any) -> None:
        captured.update(kwargs)

    monkeypatch.setattr(view_cli, "view", fake_view)
    monkeypatch.setattr(view_cli, "process_common_options", lambda _options: None)
    monkeypatch.setattr(view_cli, "resolve_view_authorization", lambda: "secret")

    result = CliRunner().invoke(
        view_cli.view_command,
        [],
        standalone_mode=False,
    )

    assert result.exit_code == 0, result.output
    assert captured["authorization"] == "secret"


def test_view_policy_errors_are_usage_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_view(**_kwargs: Any) -> None:
        raise ViewerNetworkPolicyError("unsafe viewer configuration")

    monkeypatch.setattr(view_cli, "view", fake_view)
    monkeypatch.setattr(view_cli, "process_common_options", lambda _options: None)
    monkeypatch.setattr(view_cli, "resolve_view_authorization", lambda: None)

    result = CliRunner().invoke(
        view_cli.view_command,
        [],
        standalone_mode=False,
    )

    assert isinstance(result.exception, click.UsageError)
    assert "unsafe viewer configuration" in str(result.exception)
