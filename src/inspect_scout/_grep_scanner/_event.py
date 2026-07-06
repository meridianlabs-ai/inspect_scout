"""Event to string conversion for grep_scanner pattern matching.

Re-exports the shared implementation from ``_transcript.event_text``.
"""

from inspect_scout._transcript.event_text import event_as_str

__all__ = ["event_as_str"]
