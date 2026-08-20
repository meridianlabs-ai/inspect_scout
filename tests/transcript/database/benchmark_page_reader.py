"""Peak-RSS benchmark for the parquet page reader. Not collected by pytest.

Run each mode in its OWN process (ru_maxrss is process-wide):

  .venv/bin/python tests/transcript/database/benchmark_page_reader.py --mb 200
  .venv/bin/python tests/transcript/database/benchmark_page_reader.py --mb 200 --fallback

ru_maxrss is KILOBYTES on Linux (bytes on macOS).
"""

import argparse
import asyncio
import resource
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

import inspect_scout._transcript.database.parquet.transcripts as transcripts_module
from inspect_ai.model._chat_message import ChatMessageUser
from inspect_scout._transcript.database.parquet import ParquetTranscriptsDB
from inspect_scout._transcript.types import Transcript


def _rss_kb() -> int:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss


async def run(mb: int, fallback: bool) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        location = Path(tmp) / "store"
        location.mkdir()
        db = ParquetTranscriptsDB(str(location))
        await db.connect()
        # non-ASCII so str widening would show up if a cell materialized
        content = "héllo→世界 " + "x" * (mb * 1024 * 1024)
        await db.insert(
            [
                Transcript(
                    transcript_id="bench-000",
                    source_type="bench",
                    metadata={},
                    messages=[ChatMessageUser(content=content)],
                    events=[],
                )
            ]
        )
        await db.commit()
        del content

        if fallback:

            def boom(*args: Any, **kwargs: Any) -> Any:
                raise RuntimeError("page reader disabled for benchmark")

            transcripts_module.ParquetContentReader = boom  # type: ignore[attr-defined,assignment]

        baseline_kb = _rss_kb()
        start = time.monotonic()
        infos = [info async for info in db.select()]
        result = await db.read_messages_events(infos[0])
        total = 0
        async with result.data as data:
            async for chunk in data:
                total += len(chunk)
        elapsed = time.monotonic() - start
        await db.disconnect()
        print(
            f"mode={'duckdb-fallback' if fallback else 'page-reader'} "
            f"content={mb}MB streamed={total:,}B "
            f"peak_delta={(_rss_kb() - baseline_kb) / 1024:.1f}MB "
            f"time={elapsed:.2f}s"
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mb", type=int, default=100)
    parser.add_argument("--fallback", action="store_true")
    args = parser.parse_args()
    asyncio.run(run(args.mb, args.fallback))
    return 0


if __name__ == "__main__":
    sys.exit(main())
