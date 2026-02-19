"""Save or check timeline baselines for refactoring safety.

Usage:
    python baselines.py --save   # Generate baselines
    python baselines.py --check  # Compare against saved baselines
"""

import asyncio
import difflib
import sys
from pathlib import Path

from inspect_scout import TranscriptContent, build_timeline, transcripts_from

BASELINES_DIR = Path(__file__).parent / "baselines"
DB_DIR = Path(__file__).parent / "cc-transcripts"


async def save_baselines() -> None:
    """Generate and save baseline files for all transcripts."""
    BASELINES_DIR.mkdir(exist_ok=True)
    count = 0

    async with transcripts_from(str(DB_DIR)).reader() as reader:
        async for t in reader.index():
            transcript = await reader.read(t, TranscriptContent(events="all"))
            timeline = build_timeline(transcript.events)
            tid = t.transcript_id

            timeline_json = timeline.model_dump_json(indent=2)
            repr_str = repr(timeline)

            (BASELINES_DIR / f"{tid}.timeline").write_text(timeline_json + "\n")
            (BASELINES_DIR / f"{tid}.repr").write_text(repr_str + "\n")
            count += 1
            print(f"  saved {tid[:12]}  ({len(transcript.events)} events)")

    print(f"\nSaved {count} baselines to {BASELINES_DIR}")


async def check_baselines() -> bool:
    """Compare current output against saved baselines. Returns True if all match."""
    if not BASELINES_DIR.exists():
        print("ERROR: No baselines directory found. Run with --save first.")
        return False

    failures: list[str] = []
    checked = 0

    async with transcripts_from(str(DB_DIR)).reader() as reader:
        async for t in reader.index():
            transcript = await reader.read(t, TranscriptContent(events="all"))
            timeline = build_timeline(transcript.events)
            tid = t.transcript_id

            for ext, current in [
                (".timeline", timeline.model_dump_json(indent=2) + "\n"),
                (".repr", repr(timeline) + "\n"),
            ]:
                baseline_path = BASELINES_DIR / f"{tid}{ext}"
                if not baseline_path.exists():
                    failures.append(f"{tid[:12]}{ext}: baseline file missing")
                    continue

                saved = baseline_path.read_text()
                if saved != current:
                    # Show a concise diff
                    diff = list(
                        difflib.unified_diff(
                            saved.splitlines(keepends=True),
                            current.splitlines(keepends=True),
                            fromfile=f"baseline/{tid[:12]}{ext}",
                            tofile=f"current/{tid[:12]}{ext}",
                            n=3,
                        )
                    )
                    diff_preview = "".join(diff[:40])
                    failures.append(f"{tid[:12]}{ext}: DIFFERS\n{diff_preview}")
                else:
                    checked += 1

    if failures:
        print(f"FAILURES ({len(failures)}):\n")
        for f in failures:
            print(f"  {f}\n")
        print(f"{checked} files matched, {len(failures)} differed")
        return False
    else:
        print(f"All {checked} baseline files match.")
        return True


async def main() -> None:
    if "--save" in sys.argv:
        await save_baselines()
    elif "--check" in sys.argv:
        ok = await check_baselines()
        sys.exit(0 if ok else 1)
    else:
        print("Usage: python baselines.py --save | --check")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
