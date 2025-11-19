from pathlib import Path
from typing import Literal

PKG_NAME = "inspect_scout"
PKG_PATH = Path(__file__).parent.parent
DEFAULT_DISPLAY = "rich"
DEFAULT_MAX_TRANSCRIPTS = 25
DEFAULT_BATCH_SIZE = 100
DEFAULT_SERVER_HOST = "127.0.0.1"

TRANSCRIPT_SOURCE_EVAL_LOG: Literal["eval_log", "database"] = "eval_log"
TRANSCRIPT_SOURCE_DATABASE: Literal["eval_log", "database"] = "database"
