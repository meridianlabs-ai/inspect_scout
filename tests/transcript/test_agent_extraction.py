"""Tests for agent and agent_args extraction from eval logs.

These tests verify that when eval.solver is None, the agent is correctly
extracted from plan.steps[-1].solver (and agent_args from plan.steps[-1].params).
"""

from pathlib import Path

import pytest
from inspect_scout import transcripts_from
from inspect_scout._transcript.transcripts import Transcripts

# Path to test logs (all have eval.solver: None and use plan.steps)
TEST_LOGS_DIR = Path(__file__).parent.parent / "recorder" / "logs"


@pytest.fixture
def log_transcripts() -> Transcripts:
    """Load transcripts from test eval logs."""
    return transcripts_from(str(TEST_LOGS_DIR))


@pytest.mark.asyncio
async def test_agent_from_plan_when_no_top_level_solver(
    log_transcripts: Transcripts,
) -> None:
    """Verify agent is extracted from plan.steps[-1] when eval.solver is None.

    All test logs have:
    - eval.solver: None (no externally-specified solver)
    - plan.steps with 2 steps, last step is 'generate'

    The _agent() function should fall back to plan.steps[-1].solver.
    """
    async with log_transcripts.reader() as reader:
        transcripts = [info async for info in reader.index()]

    # Verify we have transcripts to test
    assert len(transcripts) > 0, "Expected test logs to be loaded"

    # All test logs should have agent='generate' (from plan.steps[-1].solver)
    for transcript in transcripts:
        assert transcript.agent == "generate", (
            f"Expected agent='generate' from plan.steps[-1].solver, "
            f"got '{transcript.agent}' for transcript {transcript.transcript_id}"
        )


@pytest.mark.asyncio
async def test_agent_args_from_plan_when_no_top_level_solver(
    log_transcripts: Transcripts,
) -> None:
    """Verify agent_args is extracted from plan.steps[-1].params when no solver.

    All test logs have plan.steps[-1].params = {} (empty dict).
    The _agent_args() function should fall back to plan.steps[-1].params.
    """
    async with log_transcripts.reader() as reader:
        transcripts = [info async for info in reader.index()]

    # Verify we have transcripts to test
    assert len(transcripts) > 0, "Expected test logs to be loaded"

    # All test logs should have agent_args={} (from plan.steps[-1].params)
    for transcript in transcripts:
        assert transcript.agent_args == {}, (
            f"Expected agent_args={{}} from plan.steps[-1].params, "
            f"got '{transcript.agent_args}' for transcript {transcript.transcript_id}"
        )


@pytest.mark.asyncio
async def test_multiple_logs_with_plan_fallback(log_transcripts: Transcripts) -> None:
    """Verify agent extraction works across all test logs.

    This is an integration test that confirms the fallback logic works
    correctly for multiple eval logs with different plan configurations:
    - popularity: plan.steps = [system_message, generate]
    - security-guide: plan.steps = [system_message, generate]
    - theory-of-mind: plan.steps = [chain_of_thought, generate]
    - websearch: plan.steps = [use_tools, generate]

    All should extract 'generate' as the agent (last step).
    """
    async with log_transcripts.reader() as reader:
        transcripts = [info async for info in reader.index()]

    # We expect at least 4 log files with multiple samples each
    assert len(transcripts) >= 4, (
        f"Expected at least 4 transcripts, got {len(transcripts)}"
    )

    # Group by source to verify each log file contributes transcripts
    source_ids = {t.source_id for t in transcripts}
    assert len(source_ids) >= 4, (
        f"Expected at least 4 different source logs, got {len(source_ids)}"
    )

    # All should have agent='generate' from plan fallback
    for transcript in transcripts:
        assert transcript.agent == "generate"
        assert transcript.agent_args == {}
