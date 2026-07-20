"""Shared builders for the ATIF source tests.

Imported by the test modules after their `pytest.importorskip("harbor")`, so this
module can import harbor at top level (it is never collected on its own).
"""

from pathlib import Path

from harbor.models.trajectories import Agent, Step, Trajectory


def make_trajectory(steps: list[Step], **kwargs: object) -> Trajectory:
    """Build a Trajectory with a default agent/session for tests."""
    return Trajectory(
        session_id="test-session",
        agent=Agent(name="test-agent", version="0.1.0"),
        steps=steps,
        **kwargs,
    )


def write_trajectory(path: Path, trajectory: Trajectory) -> None:
    """Serialize a trajectory to JSON on disk."""
    path.write_text(trajectory.model_dump_json(exclude_none=True))
