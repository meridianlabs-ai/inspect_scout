"""OpenClaw telemetry-hal file discovery and reading utilities."""

import json
from logging import getLogger
from os import PathLike
from pathlib import Path
from typing import Any, Iterator

logger = getLogger(__name__)

# https://github.com/sage-princeton/openclaw-telemetry-hal
OPENCLAW_TELEMETRY_HAL_SOURCE_TYPE = "openclaw_telemetry_hal"


def discover_telemetry_files(path: str | PathLike[str]) -> list[Path]:
    """Discover OpenClaw telemetry files.

    Args:
        path: Path to search (the plugin's default output is
          ``~/.openclaw/logs/telemetry.jsonl``).

    Returns:
        List of telemetry file paths, sorted by modification time (newest first).
    """
    p = Path(path).expanduser()
    if not p.exists():
        logger.warning(f"Path does not exist: {p}")
        return []
    if p.is_file():
        return [p]
    return sorted(p.glob("*.jsonl"), key=lambda f: f.stat().st_mtime, reverse=True)


def read_telemetry_events(path: Path) -> Iterator[dict[str, Any]]:
    """Stream raw events from an OpenClaw telemetry file, one per line.

    Yields parsed event dicts lazily so the caller never has to hold the whole
    file in memory at once. This matters: telemetry files routinely run ~1GiB
    because every ``agent.*`` event re-dumps a CUMULATIVE ``messages[]`` snapshot
    (turn *k* recurs in every later snapshot), so the on-disk size is roughly
    quadratic in the number of turns even though the unique content is small.
    Materializing every duplicated event as a live dict would balloon to several
    times the file size in RAM; streaming lets the consumer's dedup keep only the
    distinct turns resident.

    Args:
        path: Path to the telemetry file.

    Yields:
        Parsed raw events (dicts). Malformed lines are skipped with a logged
        count once the file is fully consumed.
    """
    n_bad = 0
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                n_bad += 1
                continue
            if isinstance(event, dict):
                yield event
    if n_bad:
        logger.warning("Skipped %d malformed JSONL line(s) in %s", n_bad, path)
