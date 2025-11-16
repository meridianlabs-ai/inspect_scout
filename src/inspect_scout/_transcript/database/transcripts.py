from typing import overload, override

from inspect_scout._scanspec import ScanTranscripts

from ..transcripts import Transcripts, TranscriptsReader
from .database import TranscriptDB
from .reader import TranscriptsDBReader


class TranscriptsDBTranscripts(Transcripts):
    @overload
    def __init__(self, source: TranscriptDB) -> None: ...

    @overload
    def __init__(self, source: ScanTranscripts) -> None: ...

    def __init__(self, source: TranscriptDB | ScanTranscripts) -> None:
        if isinstance(source, TranscriptDB):
            self._db = source
            self._content_db = source
        else:
            # TODO: create in-memory database for ScanTranscripts
            # and then create separate db for reading content
            self._db = TranscriptDB("foo")
            self._content_db = TranscriptDB("foo")

    @override
    def reader(self) -> TranscriptsReader:
        return TranscriptsDBReader(self._db, self._content_db, query=self._query)


def transcripts_from(location: str) -> Transcripts:
    db = TranscriptDB(location)
    return TranscriptsDBTranscripts(db)
