from typing import AsyncIterator, Protocol, runtime_checkable

from ...types import Transcript


@runtime_checkable
class TranscriptsSource(Protocol):
    """Source that yields an async iterator of `Transcript`."""

    def __call__(self) -> AsyncIterator[Transcript]:
        """Async iterator of transcripts."""
        ...
