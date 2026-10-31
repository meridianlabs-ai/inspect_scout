"""Every action and reusable workflow in .github/workflows is pinned to a commit.

A tag or branch can be moved to new code; a commit SHA cannot. The trailing
`# vX.Y.Z` comment records the version so Dependabot and reviewers can read it.
"""

import pathlib
import re
from collections.abc import Iterator
from typing import Any

import yaml

WORKFLOWS = pathlib.Path(__file__).parents[1] / ".github" / "workflows"

PINNED = re.compile(r"[^@\s]+@[0-9a-f]{40}")

# References allowed to stay unpinned, each with the reason.
ALLOWED_UNPINNED = {
    # Shared agent stubs that track main across Meridian repos. Pinning them
    # is a decision for the meridianlabs-ai/agents owners.
    "meridianlabs-ai/agents/.github/workflows/claude.yml@main",
    "meridianlabs-ai/agents/.github/workflows/claude-review.yml@main",
    # Pinned by the PRs that split publish.yaml and npm-publish.yml; remove
    # once both have merged.
    "meridianlabs-ai/actions/slack-approval-ping@v1",
}


def workflow_uses(workflow: dict[str, Any]) -> Iterator[str]:
    """Yield each `uses:` value: job-level reusable calls and step actions."""
    for job in (workflow.get("jobs") or {}).values():
        if "uses" in job:
            yield job["uses"]
        for step in job.get("steps") or []:
            if "uses" in step:
                yield step["uses"]


def test_workflow_uses_are_pinned_to_commits() -> None:
    checked = 0
    unpinned: set[str] = set()
    for path in sorted([*WORKFLOWS.glob("*.yml"), *WORKFLOWS.glob("*.yaml")]):
        text = path.read_text()
        for uses in workflow_uses(yaml.safe_load(text)):
            checked += 1
            if uses.startswith("./") or uses in ALLOWED_UNPINNED:
                continue
            trailers = re.findall(
                rf"uses:\s*{re.escape(uses)}(.*)$", text, re.MULTILINE
            )
            commented = bool(trailers) and all(
                re.match(r"\s+#\s*\S", trailer) for trailer in trailers
            )
            if not PINNED.fullmatch(uses) or not commented:
                unpinned.add(f"{path.name}: {uses}")
    assert checked > 0, f"no `uses:` found under {WORKFLOWS}"
    assert not unpinned, (
        "pin these to a full commit SHA with a version comment "
        "(`owner/repo@<sha> # vX.Y.Z`):\n" + "\n".join(sorted(unpinned))
    )
