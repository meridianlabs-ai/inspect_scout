"""Populate a transcript database with OpenCode sessions.

Reads sessions from OpenCode's SQLite database at
~/.local/share/opencode/opencode.db by default.
"""

import asyncio

from inspect_scout import transcripts_db
from inspect_scout.sources import opencode


async def main() -> None:
    async with transcripts_db("examples/sources/opencode/transcripts") as db:
        await db.insert(opencode())


if __name__ == "__main__":
    asyncio.run(main())
