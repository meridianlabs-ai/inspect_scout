"""Populate a transcript database with Logfire traces.

Requires LOGFIRE_READ_TOKEN environment variable.
"""

import asyncio

from inspect_scout import transcripts_db
from inspect_scout.sources import logfire


async def main() -> None:
    async with transcripts_db("examples/sources/logfire/transcripts") as db:
        await db.insert(logfire())


if __name__ == "__main__":
    asyncio.run(main())
