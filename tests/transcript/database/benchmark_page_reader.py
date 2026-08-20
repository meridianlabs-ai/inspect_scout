"""Peak-RSS benchmark for the parquet page reader. Not collected by pytest.

`resource.getrusage(...).ru_maxrss` is a monotonic, process-wide high-water
mark: it never decreases within a process. Two things follow from that:

1. Building the transcript store (`insert()` + `commit()` of one large
   content cell) itself peaks well above the subsequent read cost, so
   measuring "baseline before read, delta after read" in the SAME process
   that built the store just captures write-path noise, not read-path cost.
2. Less obviously: spawning a child with `subprocess.run()` from a process
   that has already allocated a lot of memory does NOT give the child a
   clean baseline either. On Linux, the child's `ru_maxrss` high-water mark
   starts from however many pages were resident in the parent at fork
   time (verified empirically on this system) -- `execve()` in the child
   does not reset it. So the process that DOES the spawning must itself
   stay memory-light for its whole lifetime, not just "not read the
   content".

To keep the comparison honest -- one path, one sample, one process, and the
process that spawns that one sample must itself never carry the large
content -- this script's `main()` is a thin orchestrator that never touches
the content directly: it delegates the store build AND each of the two
reads to its own freshly exec'd child process (`--build` / `--read`).

Run:

  .venv/bin/python tests/transcript/database/benchmark_page_reader.py --mb 100

ru_maxrss is KILOBYTES on Linux (bytes on macOS).
"""

import argparse
import asyncio
import resource
import subprocess
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


async def _build_store(location: Path, mb: int) -> None:
    """Write one large-content transcript into a fresh store.

    Runs only in a `--build` child process, never in the orchestrator.
    """
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
    await db.disconnect()


async def _read_once(location: Path, mb: int, fallback: bool) -> None:
    """Measure peak RSS for exactly one read mode.

    Runs only in a `--read` child process, never in the orchestrator.
    """
    # Baseline captured as the first real action in this process, before any
    # store connection, so the delta below reflects only the read that follows.
    baseline_kb = _rss_kb()

    if fallback:

        def boom(*args: Any, **kwargs: Any) -> Any:
            raise RuntimeError("page reader disabled for benchmark")

        transcripts_module.ParquetContentReader = boom  # type: ignore[attr-defined,assignment]

    start = time.monotonic()
    db = ParquetTranscriptsDB(str(location))
    await db.connect()
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


def _spawn(extra_args: list[str]) -> None:
    """Exec a fresh child of this script; its stdout passes straight through."""
    subprocess.run([sys.executable, __file__, *extra_args], check=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mb", type=int, default=100, help="Size in MB of the content cell."
    )
    parser.add_argument(
        "--fallback",
        action="store_true",
        help="--read mode only: disable the page reader to measure the "
        "duckdb full-cell fallback.",
    )
    parser.add_argument(
        "--read",
        type=str,
        default=None,
        metavar="STORE_DIR",
        help="Child mode: measure one read against an existing store and "
        "exit. Set internally when the orchestrator spawns child processes.",
    )
    parser.add_argument(
        "--build",
        type=str,
        default=None,
        metavar="STORE_DIR",
        help="Child mode: write the benchmark store and exit. Set "
        "internally when the orchestrator spawns child processes.",
    )
    args = parser.parse_args()

    if args.build is not None:
        asyncio.run(_build_store(Path(args.build), args.mb))
        return 0

    if args.read is not None:
        asyncio.run(_read_once(Path(args.read), args.mb, args.fallback))
        return 0

    # Orchestrator: must stay memory-light for its whole lifetime (children
    # inherit its resident-page high-water mark at fork; see module docstring).
    with tempfile.TemporaryDirectory() as tmp:
        location = Path(tmp) / "store"
        location.mkdir()
        mb_str = str(args.mb)
        _spawn(["--build", str(location), "--mb", mb_str])
        _spawn(["--read", str(location), "--mb", mb_str])
        _spawn(["--read", str(location), "--mb", mb_str, "--fallback"])

    return 0


if __name__ == "__main__":
    sys.exit(main())
