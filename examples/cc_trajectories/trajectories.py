# To run this code you need to be on the 'feature/transcript-nodes'
# branch of inspect_scout

from inspect_scout import (
    build_timeline,
    span_messages,
)
from inspect_scout.sources import claude_code


async def main() -> None:
    async for transcript in claude_code(
        # path to claude code rollouts (defaults to ~/.claude/projects/)
        path=None,
        # remove to read all rollouts
        limit=50,
    ):
        # build timeline
        timeline = build_timeline(transcript.events)
        print(transcript.source_uri)

        # extract compaction steps from main thread
        steps = span_messages(timeline, split_compactions=True)
        for i in range(1, len(steps) + 1):
            print(f"  step {i}: {len(steps[i - 1])} messages")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
