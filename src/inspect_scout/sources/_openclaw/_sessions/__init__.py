"""OpenClaw native session importer.

Imports the session bundles OpenClaw writes under
``~/.openclaw/agents/<agent>/sessions/``. See the design doc
``design/openclaw-sessions.md`` for the schema analysis and decisions.
"""

from .client import OPENCLAW_SOURCE_TYPE
from .transcripts import openclaw

__all__ = ["openclaw", "OPENCLAW_SOURCE_TYPE"]
