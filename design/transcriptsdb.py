from types import TracebackType
from typing import AsyncIterator, Iterable, Protocol, Type, overload

from inspect_scout._scanspec import ScanTranscripts
from inspect_scout._transcript.metadata import Condition
from inspect_scout._transcript.transcripts import Transcripts
from inspect_scout._transcript.types import (
    Transcript,
    TranscriptContent,
    TranscriptInfo,
)


class TranscriptSource(Protocol):
    def __call__(self) -> AsyncIterator[Transcript]: ...


class TranscriptDB:
    @overload
    def __init__(self, transcripts: str) -> None: ...

    @overload
    def __init__(self, transcripts: ScanTranscripts) -> None: ...

    def __init__(self, transcripts: str | ScanTranscripts) -> None:
        if isinstance(transcripts, str):
            self._location: str | None = transcripts
            self._snapshot: ScanTranscripts | None = None
        else:
            self._location = None
            self._snapshot = None

    async def connect(self) -> None:
        pass

    async def disconnect(self) -> None:
        pass

    async def __aenter__(self) -> "TranscriptDB":
        await self.connect()
        return self

    async def __aexit__(
        self,
        exc_type: Type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool | None:
        await self.disconnect()
        return None

    async def count(
        self,
        where: list[Condition],
        limit: int | None = None,
    ) -> int:
        return 0

    async def query(
        self,
        where: list[Condition],
        limit: int | None = None,
        shuffle: bool | int = False,
    ) -> AsyncIterator[TranscriptInfo]:
        # when we are restored from a snapshot this is hard coded
        yield TranscriptInfo(id="id", source_id="source_id", source_uri="source_uri")

    async def read(self, t: TranscriptInfo, content: TranscriptContent) -> Transcript:
        return Transcript(id=t.id, source_id=t.source_id, source_uri=t.source_uri)

    async def insert(self, transcripts: AsyncIterator[Transcript]) -> None:
        pass

    async def update(self, transcripts: Iterable[tuple[str, Transcript]]) -> None:
        pass

    async def delete(self, transcripts: Iterable[str]) -> None:
        pass

    async def snapshot(self) -> ScanTranscripts:
        # this will be the current index
        return ScanTranscripts(type="foo", fields=[], count=0, data="")

    # restoring the snapshot will amount to creating a hard-coded where
    # whery on the entire thing
