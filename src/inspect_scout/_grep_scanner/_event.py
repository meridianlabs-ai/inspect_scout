"""Event to string conversion for grep_scanner pattern matching.

The implementation now lives in the shared ``_transcript.event_text`` module
so the llm scanner can reuse it. Re-exported here for backward compatibility.
"""

from inspect_scout._transcript.event_text import event_as_str

__all__ = ["event_as_str"]
