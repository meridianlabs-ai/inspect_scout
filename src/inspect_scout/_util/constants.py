from pathlib import Path
from typing import Literal

PKG_NAME = "inspect_scout"
PKG_PATH = Path(__file__).parent.parent
DEFAULT_DISPLAY = "rich"
DEFAULT_MAX_TRANSCRIPTS = 25
DEFAULT_BATCH_SIZE = 100
DEFAULT_SERVER_HOST = "127.0.0.1"
DEFAULT_VIEW_PORT = 7576

DEFAULT_TRANSCRIPTS_DIR = "./transcripts"
DEFAULT_LOGS_DIR = "./logs"
DEFAULT_SCANS_DIR = "./scans"

TRANSCRIPT_SOURCE_EVAL_LOG: Literal["eval_log", "database"] = "eval_log"
TRANSCRIPT_SOURCE_DATABASE: Literal["eval_log", "database"] = "database"

SPOOL_THRESHOLD_BYTES: int = 64 * 1024 * 1024
"""Byte-size threshold above which transcript reads stream via disk spool instead of materializing."""

# A parquet cell is one value inside one data page, and page sizes are thrift
# i32. The empirical ceiling for a writable+readable cell is 2,147,480,000
# bytes; this constant leaves headroom. Access via the module (like
# SPOOL_THRESHOLD_BYTES) so tests can monkeypatch it.
RECORD_CELL_MAX_BYTES: int = 2_000_000_000
