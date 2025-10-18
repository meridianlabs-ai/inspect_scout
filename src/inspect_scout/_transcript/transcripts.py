import abc
from copy import deepcopy
from types import TracebackType
from typing import (
    Iterator,
)

from .._scanspec import ScanTranscripts
from .metadata import Condition
from .types import Transcript, TranscriptContent, TranscriptInfo


class Transcripts(abc.ABC):
    """Collection of transcripts for scanning.

    Transcript collections can be filtered using the `where()`,
    `limit()`, and 'shuffle()` methods. The transcripts are
    not modified in place so the filtered transcripts should be
    referenced via the return value. For example:

    ```python
    from inspect_scout import transcripts, log_metadata as m

    tr = transcripts("./logs")
    tr = tr.where(m.task_name == "cybench")
    ```
    """

    def __init__(self) -> None:
        self._where: list[Condition] = []
        self._limit: int | None = None
        self._shuffle: bool | int = False
        self._content = TranscriptContent()

    def where(self, condition: Condition) -> "Transcripts":
        """Filter the transcript collection by a `Condition`.

        Args:
           condition: Filter condition.

        Returns:
           Transcripts: Transcripts for scanning.
        """
        transcripts = deepcopy(self)
        transcripts._where.append(condition)
        return transcripts

    def limit(self, n: int) -> "Transcripts":
        """Limit the number of transcripts processed.

        Args:
            n: Limit on transcripts.

        Returns:
            Transcripts for scanning.
        """
        transcripts = deepcopy(self)
        transcripts._limit = n
        return transcripts

    def shuffle(self, seed: int | None = None) -> "Transcripts":
        """Shuffle the order of transcripts.

        Args:
            seed: Random seed for shuffling.

        Returns:
            Transcripts for scanning.
        """
        transcripts = deepcopy(self)
        transcripts._shuffle = seed if seed is not None else True
        return transcripts

    @abc.abstractmethod
    async def __aenter__(self) -> "Transcripts":
        """Enter the async context manager."""
        ...

    @abc.abstractmethod
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool | None: ...

    @abc.abstractmethod
    async def count(self) -> int:
        """Number of transcripts in collection."""
        ...

    @abc.abstractmethod
    async def index(self) -> Iterator[TranscriptInfo]:
        """Index of `TranscriptInfo` for the collection."""
        ...

    @abc.abstractmethod
    async def _read(
        self, transcript: TranscriptInfo, content: TranscriptContent
    ) -> Transcript:
        """Read transcript content.

        Args:
            transcript: Transcript to read.
            content: Content to read (e.g. specific message types, etc.)

        Returns:
            Transcript: Transcript with content.
        """
        ...

    @abc.abstractmethod
    async def snapshot(self) -> ScanTranscripts: ...
