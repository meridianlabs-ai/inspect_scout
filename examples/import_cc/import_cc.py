import asyncio

from inspect_scout import transcripts_db
from inspect_scout.sources import claude_code


async def import_cc() -> None:
    async with transcripts_db("transcripts") as db:
        await db.insert(
            claude_code(
                path=None,  # use your default cc dir at ~/.claude/projects
                limit=10,  # limit to 10 transcripts
                # from_time=,
                # to_time=
            )
        )


if __name__ == "__main__":
    asyncio.run(import_cc())
