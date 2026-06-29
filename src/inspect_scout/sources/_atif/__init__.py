"""ATIF (Agent Trajectory Interchange Format) source for Inspect Scout.

Reads ATIF trajectory.json files (per Harbor's RFC 0001) and yields them
as Scout `Transcript`s for indexing into a transcript database.
"""

from .client import ATIF_SOURCE_TYPE
from .transcripts import atif

__all__ = ["atif", "ATIF_SOURCE_TYPE"]
