"""Tests for ViewGroup argument parsing (PROJECT_DIR vs subcommand dispatch)."""

import click
from inspect_scout._cli.view import view_command


def _parse(args: list[str]) -> click.Context:
    return view_command.make_context("view", list(args))


def _protected_args(ctx: click.Context) -> list[str]:
    # click 8.2+ stores protected args privately; 8.1.x uses the public name.
    if hasattr(ctx, "_protected_args"):
        return ctx._protected_args
    return ctx.protected_args


def test_subcommand_is_dispatched_with_its_args() -> None:
    ctx = _parse(["bundle", "-o", "out"])
    assert _protected_args(ctx) == ["bundle", "-o", "out"]


def test_option_value_matching_subcommand_name_is_not_dispatched() -> None:
    ctx = _parse(["-T", "bundle"])
    assert ctx.params["transcripts"] == "bundle"
    assert _protected_args(ctx) == []


def test_project_dir_with_interspersed_options() -> None:
    ctx = _parse(["some/path", "--port", "8080"])
    assert ctx.params["project_dir"] == "some/path"
    assert ctx.params["port"] == 8080
    assert _protected_args(ctx) == []
