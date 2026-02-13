"""Populate a transcript database with Phoenix traces.

Requires PHOENIX_API_KEY and PHOENIX_COLLECTOR_ENDPOINT environment variables.
"""

import asyncio

from inspect_scout import transcripts_db
from inspect_scout.sources import phoenix


async def main() -> None:
    async with transcripts_db("examples/sources/phoenix/transcripts") as db:
        await db.insert(phoenix(project="default"))


if __name__ == "__main__":
    asyncio.run(main())
