import asyncio
import shutil
from pathlib import Path

from inspect_scout import (
    TranscriptContent,
    build_timeline,
    transcripts_db,
    transcripts_from,
)
from inspect_scout.sources import claude_code

# async def read_all_transcripts() -> None:
#     async for t in claude_code():
#         print(t.source_uri)


async def import_transcripts() -> None:
    shutil.rmtree("cc-transcripts", ignore_errors=True)
    raw_dir = Path(__file__).parent / "raw-transcripts"
    async with transcripts_db("cc-transcripts") as db:
        await db.insert(claude_code(path=raw_dir))


async def read_transcripts() -> None:
    async with transcripts_from("cc-transcripts").reader() as reader:
        async for t in reader.index():
            transcript = await reader.read(t, TranscriptContent(events="all"))
            timeline = build_timeline(transcript.events)
            print(repr(timeline))
            print("")


async def main() -> None:
    # await read_all_transcripts()
    # await import_transcripts()
    await read_transcripts()


if __name__ == "__main__":
    asyncio.run(main())
