"""Populate a transcript database with Harbor ATIF trajectories.

Imports the committed ATIF test fixtures (requires the `harbor` package).
"""

import asyncio
import json
import shutil
from pathlib import Path

from inspect_scout import transcripts_db
from inspect_scout.sources import atif


def _normalize_fixture_ids(src: Path, dst: Path) -> None:
    """Give each fixture a unique session_id so it lands as its own transcript.

    Harbor's golden fixtures all share session_id="NORMALIZED_SESSION_ID", which
    would dedupe to a single transcript on insert; use the file stem instead.
    """
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True)
    for f in src.glob("*.json"):
        d = json.loads(f.read_text())
        if d.get("session_id") == "NORMALIZED_SESSION_ID":
            d["session_id"] = f.stem
        (dst / f.name).write_text(json.dumps(d))


async def main() -> None:
    renamed = Path("examples/sources/atif/renamed-fixtures")
    _normalize_fixture_ids(Path("tests/sources/atif_source/fixtures"), renamed)
    async with transcripts_db("examples/sources/atif/transcripts") as db:
        await db.insert(atif(path=str(renamed)))


if __name__ == "__main__":
    asyncio.run(main())
