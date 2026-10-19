"""Populate a transcript database from OpenClaw telemetry-hal JSONL files.

Run from the ``examples/sources`` directory so the ``openclaw_telemetry_hal``
package resolves::

    cd examples/sources
    python -m openclaw_telemetry_hal.populate_db

By default it reads the plugin's usual output at
``~/.openclaw/logs/telemetry.jsonl``; pass a directory or a specific ``.jsonl``
file as the first argument to override.
"""

import asyncio
import sys
from pathlib import Path

from inspect_scout import transcripts_db

from . import openclaw_telemetry_hal

DEFAULT_PATH = "~/.openclaw/logs/telemetry.jsonl"
# Write the database into this example's own directory (which is .gitignored),
# not the shared examples/sources dir, regardless of the launch directory.
DB_DIR = Path(__file__).parent / "transcripts"


async def main(path: str) -> None:
    async with transcripts_db(str(DB_DIR)) as db:
        await db.insert(openclaw_telemetry_hal(path))


if __name__ == "__main__":
    telemetry_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PATH
    asyncio.run(main(telemetry_path))
