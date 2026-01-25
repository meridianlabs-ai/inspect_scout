"""Observe decorator/context manager for transcript capture.

The `observe` decorator intercepts LLM calls and writes transcripts
to the database, using implicit leaf detection for automatic write triggering.
"""

from ._observe import observe, observe_update

__all__ = [
    "observe",
    "observe_update",
]
