"""Populate a transcript database with LangSmith traces.

Requires LANGSMITH_API_KEY environment variable.
"""

import asyncio

from inspect_scout import transcripts_db
from inspect_scout.sources import langsmith


async def main() -> None:
    async with transcripts_db("examples/sources/langsmith/transcripts") as db:
        await db.insert(langsmith(project="inspect-scout-tests-v2"))


if __name__ == "__main__":
    asyncio.run(main())
