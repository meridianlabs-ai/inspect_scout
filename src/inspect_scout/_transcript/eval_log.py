import hashlib
import io
import json
import sqlite3
from datetime import datetime
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
from inspect_ai.log import EvalLog, EvalSampleSummary
from inspect_ai.log._file import (
    EvalLogInfo,
)
from inspect_ai.scorer import Value, value_to_float
from inspect_ai.util import trace_action
from typing_extensions import override

from inspect_scout._query.condition_sql import conditions_as_filter
from inspect_scout._util.async_zip import AsyncZipReader
from inspect_scout._util.constants import TRANSCRIPT_SOURCE_EVAL_LOG

from .._query import Query
from .._query.sql import SQLDialect
from .._scanspec import ScanTranscripts
from .._transcript.transcripts import Transcripts
from .caching import samples_df_with_caching
from .database.database import TranscriptsView
from .json.load_filtered import load_filtered_transcript
from .local_files_cache import LocalFilesCache, init_task_files_cache
from .transcripts import TranscriptsReader
from .types import RESERVED_COLUMNS, Transcript, TranscriptContent, TranscriptInfo
from .util import LazyJSONDict

logger = getLogger(__name__)

TRANSCRIPTS = "transcripts"
EVAL_LOG_SOURCE_TYPE = "eval_log"

Logs: TypeAlias = (
    PathLike[str] | str | EvalLogInfo | Sequence[PathLike[str] | str | EvalLogInfo]
)

# Cache for named in-memory sqlite databases (sentinel connections keep dbs alive)
_sqlite_cache: dict[str, sqlite3.Connection] = {}


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
        query: Query,
        files_cache: LocalFilesCache | None = None,
    ) -> None:
        self._db = EvalLogTranscriptsView(logs, files_cache)
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
        return self._db.select(self._query)

    @override
    async def read(
        self, transcript: TranscriptInfo, content: TranscriptContent
    ) -> Transcript:
        return await self._db.read(transcript, content)

    @override
    async def snapshot(self) -> ScanTranscripts:
        transcript_ids = await self._db.transcript_ids(self._query)
        return ScanTranscripts(
            type=TRANSCRIPT_SOURCE_EVAL_LOG,
            filter=conditions_as_filter(self._query.where),
            transcript_ids=transcript_ids,
        )


def _logs_df_from_snapshot(snapshot: ScanTranscripts) -> "pd.DataFrame":
    import pandas as pd

    # read legacy format that included the full datasets
    if snapshot.fields and snapshot.data:
        # Read CSV data from snapshot
        snapshot_df = pd.read_csv(io.StringIO(snapshot.data))

        # determine unique logs, re-read, then filter on sample_id
        snapshot_logs = snapshot_df["log"].unique().tolist()
        df = _index_logs(snapshot_logs)
        return df[df["sample_id"].isin(snapshot_df["sample_id"])]

    else:
        # re-read from index (which will be cached) then filter
        logs = {v for v in snapshot.transcript_ids.values() if v is not None}
        df = _index_logs(list(logs))
        return df[df["sample_id"].isin(snapshot.transcript_ids.keys())]


class EvalLogTranscriptsView(TranscriptsView):
    """Read-only view of eval log transcripts backed by SQLite.

    All queries operate on an in-memory SQLite database. The input (Logs or
    DataFrame) is converted to SQLite on first connect(). This conversion is
    cached using named in-memory databases with shared cache, so subsequent
    connections to the same logs reuse the existing database.
    """

    def __init__(
        self,
        logs: Logs | pd.DataFrame,
        files_cache: LocalFilesCache | None = None,
    ):
        self._files_cache = files_cache

        # pandas required
        verify_df_prerequisites()

        # store input for deferred processing in connect()
        if isinstance(logs, pd.DataFrame):
            self._cache_key: str | None = None
            self._logs_input: Logs | pd.DataFrame = logs
        else:
            self._cache_key = _compute_cache_key_from_logs(logs)
            self._logs_input = logs

        # sqlite connection (starts out none)
        self._conn: sqlite3.Connection | None = None

        # AsyncFilesystem (starts out none)
        self._fs: AsyncFilesystem | None = None

    async def connect(self) -> None:
        # Skip if already connected
        if self._conn is not None:
            return

        if self._cache_key and self._cache_key in _sqlite_cache:
            # L2 cache hit - connect to existing named in-memory db
            self._conn = sqlite3.connect(
                f"file:{self._cache_key}?mode=memory&cache=shared", uri=True
            )
        else:
            # Cache miss - build DataFrame and populate SQLite
            if isinstance(self._logs_input, pd.DataFrame):
                df = self._logs_input
            else:
                df = _index_logs(self._logs_input)

            if self._cache_key:
                self._conn = sqlite3.connect(
                    f"file:{self._cache_key}?mode=memory&cache=shared", uri=True
                )
                # Keep sentinel connection to prevent db from being destroyed
                _sqlite_cache[self._cache_key] = sqlite3.connect(
                    f"file:{self._cache_key}?mode=memory&cache=shared", uri=True
                )
            else:
                # No cache key (DataFrame input) - use anonymous memory db
                self._conn = sqlite3.connect(":memory:")

            df.to_sql(TRANSCRIPTS, self._conn, index=False, if_exists="replace")

    @override
    async def select(self, query: Query | None = None) -> AsyncIterator[TranscriptInfo]:
        assert self._conn is not None
        query = query or Query()

        # Build SQL suffix using Query
        suffix, params, register_shuffle = query.to_sql_suffix(
            SQLDialect.SQLITE, shuffle_column="sample_id"
        )
        if register_shuffle:
            register_shuffle(self._conn)

        sql = f"SELECT * FROM {TRANSCRIPTS}{suffix}"
        cursor = self._conn.execute(sql, params)

        # get column names
        column_names = [desc[0] for desc in cursor.description]

        # process and yield results
        for row in cursor:
            # create a dict of column name to value
            row_dict = dict(zip(column_names, row, strict=True))

            # extract required fields (prefer new columns, fall back to old for compatibility)
            transcript_id = row_dict.get("transcript_id") or row_dict.get("sample_id")
            transcript_source_id = row_dict.get("source_id") or row_dict.get("eval_id")
            transcript_source_uri = row_dict.get("source_uri") or row_dict.get("log")
            transcript_date = row_dict.get("date", None)
            transcript_task_set = row_dict.get("task_set", None)
            transcript_task_id = row_dict.get("task_id", None)
            transcript_task_repeat = row_dict.get("task_repeat", None)
            transcript_agent = row_dict.get("agent", None)
            transcript_agent_args = row_dict.get("agent_args", None)
            transcript_model = row_dict.get("model", None)
            transcript_model_options = row_dict.get("generate_config", None)
            transcript_score = row_dict.get("score", None)
            transcript_success = row_dict.get("success", None)
            transcript_total_time = row_dict.get("total_time", None)
            transcript_total_tokens = row_dict.get("total_tokens", None)
            transcript_error = row_dict.get("error", None)
            transcript_limit = row_dict.get("limit", None)

            # resolve json
            if transcript_agent_args is not None:
                transcript_agent_args = json.loads(transcript_agent_args)
            if transcript_model_options is not None:
                transcript_model_options = json.loads(transcript_model_options)
            if isinstance(transcript_score, str) and (
                transcript_score.startswith("{") or transcript_score.startswith("[")
            ):
                transcript_score = json.loads(transcript_score)

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
            lazy_metadata = LazyJSONDict(metadata_dict, json_keys=JSON_COLUMNS)

            # Use normal constructor for type validation/coercion, then inject LazyJSONDict
            # for metadata for lazy parsing behavior
            info = TranscriptInfo(
                transcript_id=transcript_id,
                source_type=EVAL_LOG_SOURCE_TYPE,
                source_id=transcript_source_id,
                source_uri=transcript_source_uri,
                date=transcript_date,
                task_set=transcript_task_set,
                task_id=transcript_task_id,
                task_repeat=transcript_task_repeat,
                agent=transcript_agent,
                agent_args=transcript_agent_args,
                model=transcript_model,
                model_options=transcript_model_options,
                score=transcript_score,
                success=transcript_success,
                total_time=transcript_total_time,
                total_tokens=transcript_total_tokens,
                error=transcript_error,
                limit=transcript_limit,
                metadata={},
            )
            object.__setattr__(info, "metadata", lazy_metadata)
            yield info

    @override
    async def count(self, query: Query | None = None) -> int:
        assert self._conn is not None
        query = query or Query()
        # For count, only WHERE matters (ignore limit/shuffle/order_by)
        count_query = Query(where=query.where)
        suffix, params, _ = count_query.to_sql_suffix(SQLDialect.SQLITE)
        sql = f"SELECT COUNT(*) FROM {TRANSCRIPTS}{suffix}"
        result = self._conn.execute(sql, params).fetchone()
        assert result is not None
        return int(result[0])

    @override
    async def transcript_ids(self, query: Query | None = None) -> dict[str, str | None]:
        assert self._conn is not None
        query = query or Query()

        suffix, params, register_shuffle = query.to_sql_suffix(
            SQLDialect.SQLITE, shuffle_column="sample_id"
        )
        if register_shuffle:
            register_shuffle(self._conn)

        sql = f"SELECT * FROM {TRANSCRIPTS}{suffix}"
        cursor = self._conn.execute(sql, params)
        column_names = [desc[0] for desc in cursor.description]

        result: dict[str, str | None] = {}
        for row in cursor:
            row_dict = dict(zip(column_names, row, strict=True))
            tid = row_dict.get("transcript_id") or row_dict.get("sample_id")
            uri = row_dict.get("source_uri") or row_dict.get("log")
            if tid:
                result[tid] = uri
        return result

    @override
    async def read(self, t: TranscriptInfo, content: TranscriptContent) -> Transcript:
        assert self._conn is not None
        cursor = self._conn.execute(
            f"SELECT id, epoch FROM {TRANSCRIPTS} WHERE sample_id = ?",
            (t.transcript_id,),
        )
        row = cursor.fetchone()
        assert row is not None
        id_, epoch = row
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

        if self._fs is not None:
            await self._fs.close()
            self._fs = None


def transcripts_from_logs(logs: Logs) -> Transcripts:
    """Read sample transcripts from eval logs.

    Args:
        logs: Log paths as file(s) or directories.

    Returns:
        Transcripts: Collection of transcripts for scanning.
    """
    return EvalLogTranscripts(logs)


def _index_logs(logs: Logs) -> pd.DataFrame:
    """Index eval logs into a DataFrame with two-level caching.

    Caching: Per-file DataFrames are cached via samples_df_with_caching (L1 cache).
    SQLite database caching is handled at the connection level in EvalLogTranscriptsView.

    Args:
        logs: Paths to eval log files or directories

    Returns:
        DataFrame with one row per sample from all logs
    """
    from inspect_scout._display._display import display

    with display().text_progress("Indexing", True) as progress:

        def read_samples(path: str) -> pd.DataFrame:
            with trace_action(logger, "Scout Eval Log Index", f"Indexing {path}"):
                # This cast is wonky, but the public function, samples_df, uses overloads
                # to make the return type be a DataFrame when strict=True. Since we're
                # calling the helper method, we'll just have to cast it.
                progress.update(path)
                df = cast(
                    pd.DataFrame,
                    _read_samples_df_serial(
                        [path],
                        TranscriptColumns,
                        full=False,
                        strict=True,
                        progress=False,
                    ),
                )

                # The transcript_id uses the computed sample_id
                # value, which will properly handle old eval log
                # that are missing uuids for samples (so we use the value
                # from the synthesized sample_id column rather than the `id`
                # prop from the sample itself.
                if not df.empty:
                    df["transcript_id"] = df["sample_id"]
                return df

        return samples_df_with_caching(read_samples, logs)


def _compute_cache_key_from_logs(logs: Logs) -> str:
    """Compute cache key from logs path (not etags, for speed).

    Args:
        logs: Log paths to compute key from

    Returns:
        SHA256 hash of normalized logs path as cache key
    """
    from pathlib import Path

    # Normalize logs to a canonical string representation
    if isinstance(logs, (str, PathLike)):
        key_data = str(Path(logs).resolve())
    elif isinstance(logs, EvalLogInfo):
        key_data = logs.name
    else:
        # Sequence of logs
        paths = sorted(
            str(Path(log).resolve()) if isinstance(log, (str, PathLike)) else log.name
            for log in logs
        )
        key_data = json.dumps(paths)

    return hashlib.sha256(key_data.encode()).hexdigest()


def sample_score(sample: EvalSampleSummary) -> Value | None:
    if not sample.scores:
        return None

    score = next(iter(sample.scores.values()), None)
    if score is None:
        return None

    if isinstance(score.value, dict) and "value" in score.value:
        return score.value.get("value", None)
    else:
        return score.value


def sample_success(sample: EvalSampleSummary) -> bool | None:
    if not sample.scores:
        return None

    score = next(iter(sample.scores.values()), None)
    if not score:
        return None

    # scores can explicitly mark themselves as successful/unsuccesful
    if score.metadata and "success" in score.metadata:
        success = score.metadata.get("success", None)
        if isinstance(success, bool | None):
            return success

    # otherwise use standard value_to_float on scalers
    if isinstance(score.value, str | int | float | bool):
        return value_to_float()(score.value) > 0
    # lists/dicts get None
    else:
        return None


# Standard transcript column extractors
def _source_type(log: EvalLog) -> str:
    """Return constant source type for eval logs."""
    return EVAL_LOG_SOURCE_TYPE


def _source_id(log: EvalLog) -> str | None:
    """Return eval_id as source_id."""
    return log.eval.eval_id


def _source_uri(log: EvalLog) -> str | None:
    """Return log location as source_uri (plain path without file:// prefix)."""
    location = log.location
    if location and location.startswith("file://"):
        # Strip file:// prefix to get plain path
        return location[7:]
    return location


def _agent(log: EvalLog) -> str | None:
    if log.eval.solver is not None:
        return log.eval.solver
    elif len(log.plan.steps) > 0:
        return log.plan.steps[-1].solver
    else:
        return None


def _agent_args(log: EvalLog) -> dict[str, Any] | None:
    if log.eval.solver is not None:
        return log.eval.solver_args
    elif len(log.plan.steps) > 0:
        return log.plan.steps[-1].params
    else:
        return None


TranscriptColumns: list[Column] = (
    EvalId
    + EvalLogPath
    + [
        # Standard transcript columns (aliases for filtering)
        EvalColumn("source_type", path=_source_type, required=True),
        EvalColumn("source_id", path=_source_id, required=True),
        EvalColumn("source_uri", path=_source_uri, required=True),
        # Eval info columns
        EvalColumn("date", path="eval.created", type=datetime, required=True),
        EvalColumn("eval_status", path="status", required=True),
        EvalColumn("eval_tags", path="eval.tags", default="", value=list_as_str),
        EvalColumn("eval_metadata", path="eval.metadata", default={}),
        EvalColumn("task_set", path="eval.task", required=True, value=remove_namespace),
        EvalColumn("task_args", path="eval.task_args", default={}),
        EvalColumn("agent", path=_agent),
        EvalColumn("agent_args", path=_agent_args, default={}),
        EvalColumn("model", path="eval.model", required=True),
        EvalColumn("model_options", path="eval.model_generate_config", default={}),
        EvalColumn("generate_config", path="eval.model_generate_config", default={}),
        EvalColumn("model_roles", path="eval.model_roles", default={}),
        # Sample columns
        SampleColumn("task_id", path="id", required=True, type=str),
        SampleColumn("id", path="id", required=True, type=str),
        SampleColumn("task_repeat", path="epoch", required=True),
        SampleColumn("epoch", path="epoch", required=True),
        SampleColumn("input", path=sample_input_as_str, required=True),
        SampleColumn("target", path="target", required=True, value=list_as_str),
        SampleColumn("sample_metadata", path="metadata", default={}),
        SampleColumn("score", path=sample_score),
        SampleColumn("success", path=sample_success),
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
    "input",
    "sample_metadata",
]
