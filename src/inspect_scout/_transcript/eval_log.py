import hashlib
import io
import sqlite3
from datetime import datetime
from functools import reduce
from logging import getLogger
from os import PathLike
from types import TracebackType
from typing import (
    Any,
    AsyncIterator,
    Final,
    Sequence,
    TypeAlias,
    cast,
)

import pandas as pd
from inspect_ai._util.asyncfiles import AsyncFilesystem
from inspect_ai.analysis._dataframe.columns import Column
from inspect_ai.analysis._dataframe.evals.columns import (
    EvalColumn,
    EvalId,
    EvalLogPath,
)
from inspect_ai.analysis._dataframe.extract import (
    list_as_str,
    remove_namespace,
    score_value,
    score_values,
)
from inspect_ai.analysis._dataframe.samples.columns import SampleColumn
from inspect_ai.analysis._dataframe.samples.extract import (
    sample_input_as_str,
    sample_total_tokens,
)
from inspect_ai.analysis._dataframe.samples.table import (
    _read_samples_df_serial,
)
from inspect_ai.analysis._dataframe.util import (
    verify_prerequisites as verify_df_prerequisites,
)
from inspect_ai.log._file import (
    EvalLogInfo,
)
from inspect_ai.util import trace_action
from typing_extensions import override

from inspect_scout._util.async_zip import AsyncZipReader
from inspect_scout._util.constants import TRANSCRIPT_SOURCE_EVAL_LOG

from .._scanspec import ScanTranscripts
from .._transcript.transcripts import Transcripts
from .caching import samples_df_with_caching
from .json.load_filtered import load_filtered_transcript
from .local_files_cache import LocalFilesCache, init_task_files_cache
from .metadata import Condition
from .transcripts import TranscriptsQuery, TranscriptsReader
from .types import RESERVED_COLUMNS, Transcript, TranscriptContent, TranscriptInfo
from .util import LazyJSONDict

logger = getLogger(__name__)

TRANSCRIPTS = "transcripts"
EVAL_LOG_SOURCE_TYPE = "eval_log"

Logs: TypeAlias = (
    PathLike[str] | str | EvalLogInfo | Sequence[PathLike[str] | str | EvalLogInfo]
)


class EvalLogTranscripts(Transcripts):
    """Collection of transcripts for scanning."""

    def __init__(self, logs: Logs | ScanTranscripts) -> None:
        super().__init__()

        self._files_cache = init_task_files_cache()

        if isinstance(logs, ScanTranscripts):
            self._logs: Logs | pd.DataFrame = _logs_df_from_snapshot(logs)
        else:
            self._logs = logs

    @override
    def reader(self, snapshot: ScanTranscripts | None = None) -> TranscriptsReader:
        """Read the selected transcripts.

        Args:
            snapshot: An optional snapshot which provides hints to make the
                reader more efficient (e.g. by preventing a full scan to find
                transcript_id => filename mappings). Not used by EvalLogTranscripts.
        """
        return EvalLogTranscriptsReader(self._logs, self._query, self._files_cache)

    @staticmethod
    @override
    def from_snapshot(snapshot: ScanTranscripts) -> Transcripts:
        """Restore transcripts from a snapshot."""
        return EvalLogTranscripts(snapshot)


class EvalLogTranscriptsReader(TranscriptsReader):
    def __init__(
        self,
        logs: Logs | pd.DataFrame,
        query: TranscriptsQuery,
        files_cache: LocalFilesCache | None = None,
    ) -> None:
        self._db = EvalLogTranscriptsDB(logs, files_cache)
        self._query = query

    @override
    async def __aenter__(self) -> "TranscriptsReader":
        await self._db.connect()
        return self

    @override
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool | None:
        await self._db.disconnect()
        return None

    @override
    def index(self) -> AsyncIterator[TranscriptInfo]:
        return self._db.query(self._query.where, self._query.limit, self._query.shuffle)

    @override
    async def read(
        self, transcript: TranscriptInfo, content: TranscriptContent
    ) -> Transcript:
        return await self._db.read(transcript, content)

    @override
    async def snapshot(self) -> ScanTranscripts:
        # get the subset of the transcripts df that matches our current query
        df = self._db._transcripts_df
        sample_ids = [item.transcript_id async for item in self.index()]
        df = df[df["sample_id"].isin(sample_ids)]

        transcript_ids = df["sample_id"].to_list()
        logs = df["log"].to_list()

        return ScanTranscripts(
            type=TRANSCRIPT_SOURCE_EVAL_LOG,
            transcript_ids=dict(zip(transcript_ids, logs, strict=True)),
        )


def _logs_df_from_snapshot(snapshot: ScanTranscripts) -> "pd.DataFrame":
    import pandas as pd

    # read legacy format that included the full datasets
    if snapshot.fields and snapshot.data:
        # Read CSV data from snapshot
        df = pd.read_csv(io.StringIO(snapshot.data))

        # Process field definitions to apply correct dtypes
        for field in snapshot.fields:
            col_name = field["name"]
            col_type = field["type"]

            # Skip if column doesn't exist in DataFrame
            if col_name not in df.columns:
                continue

            # Handle datetime columns with timezone
            if col_type == "datetime":
                tz = field.get("tz")
                if tz:
                    # Parse datetime with timezone
                    df[col_name] = pd.to_datetime(df[col_name]).dt.tz_localize(tz)
                else:
                    df[col_name] = pd.to_datetime(df[col_name])

            # Handle other specific types
            elif col_type == "integer":
                # Handle nullable integers
                if df[col_name].isnull().any():
                    df[col_name] = df[col_name].astype("Int64")
                else:
                    df[col_name] = df[col_name].astype("int64")

            elif col_type == "number":
                df[col_name] = pd.to_numeric(df[col_name], errors="coerce")

            elif col_type == "boolean":
                df[col_name] = df[col_name].astype("bool")

            elif col_type == "string":
                df[col_name] = df[col_name].astype("string")

            # For any other type, let pandas infer or keep as-is

        return df

    else:
        # re-read from index (which will be cached) then filter
        logs = {v for v in snapshot.transcript_ids.values() if v is not None}
        df = _index_logs(list(logs))
        return df[df["sample_id"].isin(snapshot.transcript_ids.keys())]


class EvalLogTranscriptsDB:
    def __init__(
        self,
        logs: Logs | pd.DataFrame,
        files_cache: LocalFilesCache | None = None,
    ):
        self._files_cache = files_cache

        # pandas required
        verify_df_prerequisites()
        import pandas as pd

        # resolve logs or df to transcript_df (sample per row)
        if not isinstance(logs, pd.DataFrame):
            self._transcripts_df = _index_logs(logs)
        else:
            self._transcripts_df = logs

        # sqlite connection (starts out none)
        self._conn: sqlite3.Connection | None = None

        # AsyncFilesystem (starts out none)
        self._fs: AsyncFilesystem | None = None

        # Track current shuffle seed for UDF registration
        self._current_shuffle_seed: int | None = None

    def _register_shuffle_function(self, seed: int) -> None:
        """Register SQLite UDF for deterministic shuffling with given seed.

        Args:
            seed: Random seed for deterministic shuffling.
        """
        assert self._conn is not None

        # Only re-register if seed changed
        if self._current_shuffle_seed == seed:
            return

        def shuffle_hash(sample_id: str) -> str:
            """Compute deterministic hash for shuffling."""
            content = f"{sample_id}:{seed}"
            return hashlib.sha256(content.encode()).hexdigest()

        self._conn.create_function("shuffle_hash", 1, shuffle_hash)
        self._current_shuffle_seed = seed

    async def connect(self) -> None:
        # Skip if already connected
        if self._conn is not None:
            return
        self._conn = sqlite3.connect(":memory:")
        self._transcripts_df.to_sql(
            TRANSCRIPTS, self._conn, index=False, if_exists="replace"
        )

    async def query(
        self,
        where: list[Condition] | None = None,
        limit: int | None = None,
        shuffle: bool | int = False,
    ) -> AsyncIterator[TranscriptInfo]:
        assert self._conn is not None

        # build sql with where clause
        where_clause, where_params = self._build_where_clause(where)
        sql = f"SELECT * FROM {TRANSCRIPTS}{where_clause}"

        # add ORDER BY if shuffle is enabled
        if shuffle:
            # If shuffle is True, use a default seed of 0; otherwise use the provided seed
            seed = 0 if shuffle is True else shuffle
            self._register_shuffle_function(seed)
            sql += " ORDER BY shuffle_hash(sample_id)"

        # add LIMIT to SQL if specified
        sql_params = where_params.copy()
        if limit is not None:
            sql += " LIMIT ?"
            sql_params.append(limit)

        # execute the query
        cursor = self._conn.execute(sql, sql_params)

        # get column names
        column_names = [desc[0] for desc in cursor.description]

        # process and yield results
        for row in cursor:
            # create a dict of column name to value
            row_dict = dict(zip(column_names, row, strict=True))

            # extract required fields
            transcript_id = row_dict.get("sample_id", None)
            transcript_source_id = row_dict.get("eval_id", None)
            transcript_source_uri = row_dict.get("log", None)

            # ensure we have required fields
            if (
                transcript_id is None
                or transcript_source_id is None
                or transcript_source_uri is None
            ):
                raise ValueError(
                    f"Missing required fields: sample_id={transcript_id}, log={transcript_source_uri}"
                )

            # everything else goes into metadata (excluding reserved columns)
            # Use LazyJSONDict with JSON_COLUMNS to defer JSON parsing until accessed
            metadata_dict = {
                k: v
                for k, v in row_dict.items()
                if v is not None and k not in RESERVED_COLUMNS
            }
            metadata = LazyJSONDict(metadata_dict, json_keys=JSON_COLUMNS)

            # Use model_construct to bypass Pydantic validation which would
            # convert LazyJSONDict to a plain dict, defeating lazy parsing
            yield TranscriptInfo.model_construct(
                transcript_id=transcript_id,
                source_type=EVAL_LOG_SOURCE_TYPE,
                source_id=transcript_source_id,
                source_uri=transcript_source_uri,
                metadata=metadata,
            )

    async def read(self, t: TranscriptInfo, content: TranscriptContent) -> Transcript:
        id_, epoch = self._transcripts_df[
            self._transcripts_df["sample_id"] == t.transcript_id
        ].iloc[0][["id", "epoch"]]
        sample_file_name = f"samples/{id_}_epoch_{epoch}.json"

        if not self._fs:
            self._fs = AsyncFilesystem()

        source_uri = (
            ""  # always has a source_uri
            if t.source_uri is None
            else await self._files_cache.resolve_remote_uri_to_local(
                self._fs,
                t.source_uri,
            )
            if self._files_cache
            else t.source_uri
        )
        zip_reader = AsyncZipReader(self._fs, source_uri)
        with trace_action(
            logger,
            "Scout Eval Log Read",
            f"Reading from {t.source_uri} ({sample_file_name})",
        ):
            async with await zip_reader.open_member(sample_file_name) as json_iterable:
                return await load_filtered_transcript(
                    json_iterable,
                    t,
                    content.messages,
                    content.events,
                )

    async def disconnect(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None
            self._current_shuffle_seed = None

        if self._fs is not None:
            await self._fs.close()
            self._fs = None

    def _build_where_clause(
        self, where: list[Condition] | None
    ) -> tuple[str, list[Any]]:
        """Build WHERE clause and parameters from conditions.

        Args:
            where: List of conditions to combine with AND.

        Returns:
            Tuple of (where_clause, parameters). where_clause is empty string if no conditions.
        """
        if where and len(where) > 0:
            condition: Condition = (
                where[0] if len(where) == 1 else reduce(lambda a, b: a & b, where)
            )
            where_sql, where_params = condition.to_sql()
            return f" WHERE {where_sql}", where_params
        return "", []


def transcripts_from_logs(logs: Logs) -> Transcripts:
    """Read sample transcripts from eval logs.

    Args:
        logs: Log paths as file(s) or directories.

    Returns:
        Transcripts: Collection of transcripts for scanning.
    """
    return EvalLogTranscripts(logs)


def _index_logs(logs: Logs) -> pd.DataFrame:
    from inspect_scout._display._display import display

    with display().text_progress("Indexing", True) as progress:

        def read_samples(path: str) -> pd.DataFrame:
            with trace_action(logger, "Scout Eval Log Index", f"Indexing {path}"):
                # This cast is wonky, but the public function, samples_df, uses overloads
                # to make the return type be a DataFrame when strict=True. Since we're
                # calling the helper method, we'll just have to cast it.
                progress.update(path)
                return cast(
                    pd.DataFrame,
                    _read_samples_df_serial(
                        [path],
                        TranscriptColumns,
                        full=False,
                        strict=True,
                        progress=False,
                    ),
                )

        return samples_df_with_caching(read_samples, logs)


TranscriptColumns: list[Column] = (
    EvalId
    + EvalLogPath
    + [
        EvalColumn("eval_status", path="status", required=True),
        EvalColumn("eval_created", path="eval.created", type=datetime, required=True),
        EvalColumn("eval_tags", path="eval.tags", default="", value=list_as_str),
        EvalColumn("eval_metadata", path="eval.metadata", default={}),
        EvalColumn(
            "task_name", path="eval.task", required=True, value=remove_namespace
        ),
        EvalColumn("task_args", path="eval.task_args", default={}),
        EvalColumn("solver", path="eval.solver"),
        EvalColumn("solver_args", path="eval.solver_args", default={}),
        EvalColumn("model", path="eval.model", required=True),
        EvalColumn("generate_config", path="eval.model_generate_config", default={}),
        EvalColumn("model_roles", path="eval.model_roles", default={}),
        SampleColumn("id", path="id", required=True, type=str),
        SampleColumn("epoch", path="epoch", required=True),
        SampleColumn("input", path=sample_input_as_str, required=True),
        SampleColumn("target", path="target", required=True, value=list_as_str),
        SampleColumn("sample_metadata", path="metadata", default={}),
        SampleColumn("score", path="scores", value=score_value),
        SampleColumn("score_*", path="scores", value=score_values),
        SampleColumn("total_tokens", path=sample_total_tokens),
        SampleColumn("total_time", path="total_time"),
        SampleColumn("working_time", path="total_time"),
        SampleColumn("error", path="error", default=""),
        SampleColumn("limit", path="limit", default=""),
    ]
)

JSON_COLUMNS: Final[list[str]] = [
    "eval_metadata",
    "task_args",
    "solver_args",
    "generate_config",
    "model_roles",
    "sample_metadata",
]
