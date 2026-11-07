"""Import limits apply to standalone, split, and merged conversations."""

from pathlib import Path

import pytest
from inspect_scout.sources import claude_code

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "filename",
    [
        "simple_conversation.jsonl",
        "clear_split_session.jsonl",
        "slug_session_1.jsonl",
        "slug_multi_clear_file1.jsonl",
    ],
)
@pytest.mark.parametrize("limit", [None, 0, 1, 2, 100])
async def test_import_limit(filename: str, limit: int | None) -> None:
    path = FIXTURES / filename
    unlimited = [transcript async for transcript in claude_code(path)]
    assert unlimited
    limited = [transcript async for transcript in claude_code(path, limit=limit)]
    assert [t.transcript_id for t in limited] == [
        t.transcript_id for t in unlimited[:limit]
    ]
