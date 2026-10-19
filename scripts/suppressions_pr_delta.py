#!/usr/bin/env python3
"""Markdown body for the sticky PR comment on suppression ledger changes.

Prints nothing when the ledger is unchanged.

Usage: python3 suppressions_pr_delta.py <base.json> <head.json>
"""

import json
import re
import sys
from pathlib import Path

# Sibling-script import: resolves because sys.path[0] is this script's
# directory when invoked by path (as the workflow does); the test suite
# pre-registers the module in sys.modules instead.
from check_suppressions import Delta, Ledger, diff_ledgers, totals

MARKER = "<!-- suppressions-delta -->"

# Shown instead of a ledger key that check_suppressions.py could not have
# written, so a PR's hand-edited suppressions.json cannot put arbitrary text
# in the bot's comment.
UNRECOGNISED_KEY = "(unrecognised key)"

# A repo-relative .py/.pyi path, as `git ls-files` lists them.
_SEGMENT = r"(?!\.\.?(?:/|$))[A-Za-z0-9_.+-]+"
_FILE_KEY_RE = re.compile(rf"{_SEGMENT}(?:/{_SEGMENT})*\.pyi?")

# The rule keys check_suppressions._rules produces.
_RULE_KEY_RE = re.compile(
    r"(?:noqa(?::[A-Z]+[0-9]+)?"
    r"|type: ignore(?:\[[\w-]+\])?"
    r"|pyright: ignore(?:\[[\w-]+\])?"
    r"|mypy: ignore-errors"
    r"|mypy: disable-error-code\[[\w-]+\])"
    r"(?: \(file-wide\))?",
    re.ASCII,
)


def _load(path: str) -> Ledger:
    try:
        ledger: Ledger = json.loads(Path(path).read_text())
        return ledger
    except (OSError, json.JSONDecodeError):
        return {}


def _cell(value: str) -> str:
    r"""Render untrusted text as a literal code span inside a Markdown table cell.

    The fence is one backtick longer than any backtick run in the value, so
    nothing in it is parsed as Markdown. `\|` keeps a pipe from ending the
    table cell.
    """
    value = value.replace("\r", " ").replace("\n", " ").replace("|", "\\|")
    fence = "`" * (max(map(len, re.findall("`+", value)), default=0) + 1)
    # A code span strips one space from each end when both are present.
    if value[:1] in ("`", " ", "") or value[-1:] in ("`", " "):
        value = f" {value} "
    return f"{fence}{value}{fence}"


def _key_cell(value: str, pattern: re.Pattern[str]) -> str:
    """`_cell(value)` if the ledger key matches `pattern`, else a placeholder."""
    return _cell(value) if pattern.fullmatch(value) else UNRECOGNISED_KEY


def render(base: Ledger, head: Ledger) -> str | None:
    """The comment body for a base -> head ledger change, or None if none.

    An undescribed-only change (a reason added or removed) renders too:
    otherwise such a ledger diff would produce nothing and the workflow
    would falsely reset the sticky comment to "no longer changes the
    ledger".
    """
    rows = diff_ledgers(base, head)
    if not rows:
        return None

    total_before, undescribed_before = totals(base)
    total_after, undescribed_after = totals(head)
    delta = total_after - total_before
    undescribed_delta = undescribed_after - undescribed_before
    needs_attention = delta > 0 or undescribed_delta > 0
    if undescribed_delta > 0 and delta <= 0:
        heading = (
            f"⚠️ Reason-less suppressions grew: {undescribed_before} → "
            f"{undescribed_after} (+{undescribed_delta}); total "
            f"{total_before} → {total_after} ({'±0' if delta == 0 else delta})"
        )
    elif delta > 0:
        heading = (
            f"⚠️ Suppression ledger grew: {total_before} → {total_after} (+{delta})"
        )
    else:
        heading = (
            f"Suppression ledger changed: {total_before} → {total_after} "
            f"({'±0' if delta == 0 else delta})"
        )

    def render_row(row: Delta) -> str:
        file, rule = row.key
        change = row.after.total - row.before.total
        change_cell = "±0" if change == 0 else f"{change:+d}"
        reason_note = (
            ""
            if row.before.undescribed == row.after.undescribed
            else f" (reason-less {row.before.undescribed} → {row.after.undescribed})"
        )
        return (
            f"| {_key_cell(file, _FILE_KEY_RE)} | {_key_cell(rule, _RULE_KEY_RE)} "
            f"| {change_cell}{reason_note} |"
        )

    table = "\n".join(render_row(row) for row in rows)

    undescribed_line = (
        ""
        if undescribed_before == undescribed_after
        else f"\nReason-less (baselined) suppressions: "
        f"{undescribed_before} → {undescribed_after}\n"
    )

    footer = (
        "\nEvery new suppression needs a trailing `# reason` comment and "
        "maintainer sign-off of this ledger diff — see the Suppression gate "
        "section in AGENTS.md."
        if needs_attention
        else ""
    )

    return (
        f"{MARKER}\n### {heading}\n\n| File | Rule | Change |\n|---|---|---|\n"
        f"{table}\n{undescribed_line}{footer}"
    )


def main() -> int:
    base_path, head_path = sys.argv[1:3]
    body = render(_load(base_path), _load(head_path))
    if body is not None:
        print(body)
    return 0


if __name__ == "__main__":
    sys.exit(main())
