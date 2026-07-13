"""OpenClaw ``telemetry-hal`` importer.

Imports the JSONL telemetry written by the ``openclaw-telemetry-hal`` plugin
(https://github.com/sage-princeton/openclaw-telemetry-hal). These are **not**
native OpenClaw session files, which are an entirely different, richer schema.
See this example's ``README.md`` for the schema analysis and known
limitations.
"""

from .client import OPENCLAW_TELEMETRY_HAL_SOURCE_TYPE
from .transcripts import openclaw_telemetry_hal

__all__ = ["openclaw_telemetry_hal", "OPENCLAW_TELEMETRY_HAL_SOURCE_TYPE"]
