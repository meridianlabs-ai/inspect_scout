"""Populate a transcript database with Antigravity CLI conversations.

Imports the committed Antigravity test fixtures. To import your own
conversations instead, drop the `path` argument (defaults to
`~/.gemini/antigravity-cli`).
"""

import asyncio

from inspect_scout import transcripts_db
from inspect_scout.sources import antigravity


async def main() -> None:
    async with transcripts_db("examples/sources/antigravity/transcripts") as db:
        await db.insert(
            antigravity(path="tests/sources/antigravity_source/fixtures/root")
        )


if __name__ == "__main__":
    asyncio.run(main())
