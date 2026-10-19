"""Populate a transcript database with Harbor ATIF trajectories.

Requires the `harbor` package. Imports the committed ATIF test fixtures.
"""

import asyncio

from inspect_scout import transcripts_db
from inspect_scout.sources import atif


async def main() -> None:
    async with transcripts_db("examples/sources/atif/transcripts") as db:
        await db.insert(atif(path="tests/sources/atif_source/fixtures"))


if __name__ == "__main__":
    asyncio.run(main())
