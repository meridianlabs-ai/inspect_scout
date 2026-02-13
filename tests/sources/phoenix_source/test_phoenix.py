"""Integration tests for Phoenix transcript source.

These tests require:
- PHOENIX_RUN_TESTS=1
- PHOENIX_API_KEY set
- PHOENIX_COLLECTOR_ENDPOINT set (or defaults to localhost:6006)
- Test traces created via bootstrap.py
"""

import pytest

from .conftest import skip_if_no_phoenix


@skip_if_no_phoenix
@pytest.mark.asyncio
async def test_phoenix_import_basic(phoenix_project: str) -> None:
    """Test basic Phoenix import returns transcripts."""
    from inspect_scout.sources._phoenix import phoenix

    transcripts = []
    async for transcript in phoenix(project=phoenix_project, limit=5):
        transcripts.append(transcript)

    assert len(transcripts) > 0
    assert transcripts[0].source_type == "phoenix"
    assert transcripts[0].transcript_id is not None


@skip_if_no_phoenix
@pytest.mark.asyncio
async def test_phoenix_transcript_has_events(phoenix_project: str) -> None:
    """Test that imported transcripts have events."""
    from inspect_scout.sources._phoenix import phoenix

    async for transcript in phoenix(project=phoenix_project, limit=1):
        assert transcript.events is not None
        assert len(transcript.events) > 0
        break


@skip_if_no_phoenix
@pytest.mark.asyncio
async def test_phoenix_transcript_has_messages(phoenix_project: str) -> None:
    """Test that imported transcripts have messages."""
    from inspect_scout.sources._phoenix import phoenix

    async for transcript in phoenix(project=phoenix_project, limit=1):
        assert transcript.messages is not None
        assert len(transcript.messages) > 0
        break


@skip_if_no_phoenix
@pytest.mark.asyncio
async def test_phoenix_transcript_has_model(phoenix_project: str) -> None:
    """Test that imported transcripts have model info."""
    from inspect_scout.sources._phoenix import phoenix

    async for transcript in phoenix(project=phoenix_project, limit=1):
        assert transcript.model is not None
        break


@skip_if_no_phoenix
@pytest.mark.asyncio
async def test_phoenix_limit_parameter(phoenix_project: str) -> None:
    """Test that limit parameter works."""
    from inspect_scout.sources._phoenix import phoenix

    transcripts = []
    async for transcript in phoenix(project=phoenix_project, limit=2):
        transcripts.append(transcript)

    assert len(transcripts) <= 2


@skip_if_no_phoenix
@pytest.mark.asyncio
async def test_phoenix_source_metadata(phoenix_project: str) -> None:
    """Test transcript metadata fields."""
    from inspect_scout.sources._phoenix import phoenix

    async for transcript in phoenix(project=phoenix_project, limit=1):
        assert transcript.source_id == phoenix_project
        assert transcript.source_uri is not None
        assert transcript.task_set == phoenix_project
        break


@skip_if_no_phoenix
@pytest.mark.asyncio
async def test_phoenix_requires_project() -> None:
    """Test that project parameter is required."""
    from inspect_scout.sources._phoenix import phoenix

    with pytest.raises(ValueError, match="project"):
        async for _ in phoenix():
            pass
