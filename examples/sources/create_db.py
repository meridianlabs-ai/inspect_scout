"""Create a LangFuse transcript database with sample sessions.

This script fetches 4 sessions from LangFuse (one per provider format)
and stores them in a local Parquet transcript database.

Usage:
    python examples/langfuse-db/create_db.py
"""

import asyncio
from collections.abc import AsyncIterator
from pathlib import Path

from inspect_scout import transcripts_db
from inspect_scout._transcript.types import Transcript
from inspect_scout.sources import langfuse

# Session IDs for test data (one per provider format)
SESSION_IDS = {
    "bsCW6Mpd5t8y2nzwiGxzEj",  # Anthropic (OTEL with extended thinking)
    "SsZiMRBMvPH5GPnsu6Jk69",  # OpenAI Responses API
    "LhXbgLJvb4KCsuDV5rffpR",  # OpenAI Chat Completions
    "EG2UfE9MvpBSmy73R6a2UH",  # Google Gemini
}


async def main() -> None:
    # Database location (relative to this script)
    db_path = Path(__file__).parent / "transcripts"

    # Filter transcripts to only include our 4 test sessions
    async def filtered_transcripts() -> AsyncIterator[Transcript]:
        async for transcript in langfuse():
            if transcript.transcript_id in SESSION_IDS:
                yield transcript

    # Create database and insert transcripts
    async with transcripts_db(str(db_path)) as db:
        await db.insert(filtered_transcripts())

    print(f"Created database at: {db_path}")


if __name__ == "__main__":
    asyncio.run(main())
