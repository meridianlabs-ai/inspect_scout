"""No workflow grants a write permission at the workflow level.

Workflow-level permissions reach every job, including ones added later.
A workflow that needs to write sets `permissions: {}` at the top and grants
the write to the job that needs it. A workflow with no top-level
`permissions` gives each job without its own the repository's default token,
so there every job must declare its permissions.

A GitHub App token gets every permission the App has unless the step that
creates it asks for less, so each one names the permissions it needs.
"""

import pathlib

import pytest
import yaml

WORKFLOWS = pathlib.Path(__file__).parents[1] / ".github" / "workflows"
WORKFLOW_FILES = sorted([*WORKFLOWS.glob("*.yml"), *WORKFLOWS.glob("*.yaml")])
APP_TOKEN_ACTION = "actions/create-github-app-token@"


@pytest.mark.parametrize("path", WORKFLOW_FILES, ids=lambda path: path.name)
def test_workflow_level_permissions_are_read_only(path: pathlib.Path) -> None:
    workflow = yaml.safe_load(path.read_text())
    if "permissions" not in workflow:
        undeclared = [
            name for name, job in workflow["jobs"].items() if "permissions" not in job
        ]
        assert not undeclared, f"declare permissions for {undeclared}"
        return
    permissions = workflow["permissions"] or {}
    if permissions == "read-all":
        return
    assert isinstance(permissions, dict), f"workflow-level permissions: {permissions}"
    writes = {scope for scope, access in permissions.items() if access == "write"}
    assert not writes, f"grant {writes} to the job that needs it"


@pytest.mark.parametrize("path", WORKFLOW_FILES, ids=lambda path: path.name)
def test_app_tokens_name_their_permissions(path: pathlib.Path) -> None:
    workflow = yaml.safe_load(path.read_text())
    for name, job in workflow["jobs"].items():
        for step in job.get("steps", []):
            if not step.get("uses", "").startswith(APP_TOKEN_ACTION):
                continue
            inputs = step.get("with", {})
            assert any(key.startswith("permission-") for key in inputs), (
                f"{name}: set permission-<scope> inputs on {step['uses']}"
            )
