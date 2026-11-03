"""Jobs that hold credentials restore no cache.

A malicious package installed by any job can write to the shared Actions
cache, so a job holding secrets, an id-token or write permissions, or one
whose output is published, must not restore one.
"""

from pathlib import Path
from typing import Any

import pytest
import yaml

WORKFLOWS = Path(__file__).parents[1] / ".github" / "workflows"
CREDENTIAL_JOBS = [
    # Builds what the publish job uploads.
    ("publish.yaml", "build"),
    ("publish.yaml", "publish"),
    ("publish.yaml", "notify-approval"),
    ("npm-publish.yml", "notify-approval"),
    ("release-pin-deps.yml", "pin"),
]


def job_steps(workflow: str, job: str) -> list[dict[str, Any]]:
    config = yaml.safe_load((WORKFLOWS / workflow).read_text())
    steps: list[dict[str, Any]] = config["jobs"][job]["steps"]
    return steps


@pytest.mark.parametrize("workflow,job", CREDENTIAL_JOBS)
def test_credential_holding_jobs_restore_no_cache(workflow: str, job: str) -> None:
    for step in job_steps(workflow, job):
        action = step.get("uses", "").split("@")[0]
        inputs = step.get("with") or {}
        assert action not in {"actions/cache", "actions/cache/restore"}
        if action == "astral-sh/setup-uv":
            assert inputs.get("enable-cache") is False
        if action == "actions/setup-python":
            assert "cache" not in inputs
        if action == "actions/setup-node":
            assert "cache" not in inputs
            assert inputs.get("package-manager-cache") is False
