"""OpenClaw import source.

Imports native OpenClaw session bundles (the ``~/.openclaw/`` on-disk format)
via the ``openclaw`` entry point, setting ``agent="openclaw"``.
"""

from ._sessions import OPENCLAW_SOURCE_TYPE, openclaw

__all__ = [
    "openclaw",
    "OPENCLAW_SOURCE_TYPE",
]
