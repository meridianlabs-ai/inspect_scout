import hashlib
import io
import json
import sqlite3
from datetime import datetime
from functools import reduce
from types import TracebackType
from typing import (
    Any,
    AsyncIterator,
    Final,
    Type,
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
from pydantic import JsonValue
from typing_extensions import override

from inspect_scout._util.async_zip import AsyncZipReader

from .._scanspec import ScanTranscripts, TranscriptField
from .._transcript.transcripts import Transcripts
from .caching import samples_df_with_caching
from .json.load_filtered import load_filtered_transcript
from .local_files_cache import LocalFilesCache, create_temp_cache
from .metadata import Condition
from .types import LogPaths, Transcript, TranscriptContent, TranscriptInfo

TRANSCRIPTS = "transcripts"


class EvalLogTranscripts(Transcripts):
    """Collection of transcripts for scanning."""

    def __init__(self, logs: LogPaths | ScanTranscripts) -> None:
        super().__init__()
        if isinstance(logs, ScanTranscripts):
            self._logs: LogPaths | pd.DataFrame = self._logs_df_from_snapshot(logs)
        else:
            self._logs = logs
        self._db: EvalLogTranscriptsDB | None = None

    @override
    async def __aenter__(self) -> "Transcripts":
        await self.db.connect()
        return self

    @override
    async def __aexit__(
        self,
        exc_type: Type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool | None:
        await self.db.disconnect()
        return None

    @override
    async def count(self) -> int:
        return await self.db.count(self._where, self._limit)

    @override
    def index(self) -> AsyncIterator[TranscriptInfo]:
        return self.db.query(self._where, self._limit, self._shuffle)

    @override
    async def read(
        self, transcript: TranscriptInfo, content: TranscriptContent
    ) -> Transcript:
        return await self.db.read(transcript, content)

    @override
    async def snapshot(self) -> ScanTranscripts:
        # get the subset of the transcripts df that matches our current query
        df = self.db._transcripts_df
        sample_ids = [item.id async for item in self.index()]
        df = df[df["sample_id"].isin(sample_ids)]

        # get fields
        fields: list[TranscriptField] = json.loads(df.to_json(orient="table"))[
            "schema"
        ]["fields"]

        # get data as csv
        buffer = io.StringIO()
        df.to_csv(buffer, index=False)
        data = buffer.getvalue()

        return ScanTranscripts(
            type="eval_log",
            fields=fields,
            count=len(df),
            data=data,
        )

    @staticmethod
    def _logs_df_from_snapshot(snapshot: ScanTranscripts) -> "pd.DataFrame":
        import pandas as pd

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

    @property
    def db(self) -> "EvalLogTranscriptsDB":
        if self._db is None:
            if self._logs is None:
                raise RuntimeError(
                    "Attempted to use eval log transcripts without specifying 'logs'"
                )
            self._db = EvalLogTranscriptsDB(self._logs)
        return self._db


class EvalLogTranscriptsDB:
    def __init__(self, logs: LogPaths | pd.DataFrame):
        # pandas required
        verify_df_prerequisites()
        import pandas as pd

        # resolve logs or df to transcript_df (sample per row)
        if not isinstance(logs, pd.DataFrame):

            def read_samples(path: str) -> pd.DataFrame:
                # This cast is wonky, but the public function, samples_df, uses overloads
                # to make the return type be a DataFrame when strict=True. Since we're
                # calling the helper method, we'll just have to cast it.
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

            self._transcripts_df = samples_df_with_caching(read_samples, logs)
        else:
            self._transcripts_df = logs

        # sqlite connection (starts out none)
        self._conn: sqlite3.Connection | None = None

        # AsyncFilesystem (starts out none)
        self._fs: AsyncFilesystem | None = None

        # LocalFilesCache (starts out none)
        self._files_cache: LocalFilesCache | None = None

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
        self._files_cache = create_temp_cache()

    async def count(
        self,
        where: list[Condition],
        limit: int | None = None,
    ) -> int:
        assert self._conn is not None

        # build sql with where clause
        where_clause, where_params = self._build_where_clause(where)

        if limit is not None:
            # When limit is specified, we need to count from a subquery
            sql = f"SELECT COUNT(*) FROM (SELECT * FROM {TRANSCRIPTS}{where_clause} LIMIT {limit})"
        else:
            # Simple count without limit
            sql = f"SELECT COUNT(*) FROM {TRANSCRIPTS}{where_clause}"

        # execute the query
        cursor = self._conn.execute(sql, where_params)
        result = cursor.fetchone()

        return result[0] if result else 0

    async def query(
        self,
        where: list[Condition],
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

            # materialize JSON columns
            for column in JSON_COLUMNS:
                if column in row_dict:
                    row_dict[column] = json.loads(row_dict[column])

            # extract additional fields we'll use in TranscriptInfo
            score = row_dict.get("score", None)
            scores: dict[str, JsonValue] = {}
            for key, value in row_dict.items():
                if key.startswith("score_"):
                    scores[key.replace("score_", "", 1)] = value
            variables = row_dict.get("sample_metadata", {})

            # ensure we have required fields
            if (
                transcript_id is None
                or transcript_source_id is None
                or transcript_source_uri is None
            ):
                raise ValueError(
                    f"Missing required fields: sample_id={transcript_id}, log={transcript_source_uri}"
                )

            # everything else goes into metadata
            metadata = {k: v for k, v in row_dict.items() if v is not None}

            yield TranscriptInfo(
                id=transcript_id,
                source_id=transcript_source_id,
                source_uri=transcript_source_uri,
                score=score,
                scores=scores,
                variables=variables,
                metadata=metadata,
            )

    async def read(self, t: TranscriptInfo, content: TranscriptContent) -> Transcript:
        id_, epoch = self._transcripts_df[
            self._transcripts_df["sample_id"] == t.id
        ].iloc[0][["id", "epoch"]]
        sample_file_name = f"samples/{id_}_epoch_{epoch}.json"

        if not self._fs:
            self._fs = AsyncFilesystem()

        if not self._files_cache:
            self._files_cache = create_temp_cache()

        zip_reader = AsyncZipReader(
            self._fs,
            await self._files_cache.resolve_remote_uri_to_local(self._fs, t.source_uri),
        )
        async with zip_reader.open_member(sample_file_name) as json_iterator:
            return await load_filtered_transcript(
                json_iterator,
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

        if self._files_cache is not None:
            self._files_cache.cleanup()
            self._files_cache = None

    def _build_where_clause(self, where: list[Condition]) -> tuple[str, list[Any]]:
        """Build WHERE clause and parameters from conditions.

        Args:
            where: List of conditions to combine with AND.

        Returns:
            Tuple of (where_clause, parameters). where_clause is empty string if no conditions.
        """
        if len(where) > 0:
            condition: Condition = (
                where[0] if len(where) == 1 else reduce(lambda a, b: a & b, where)
            )
            where_sql, where_params = condition.to_sql()
            return f" WHERE {where_sql}", where_params
        return "", []


def transcripts_from_logs(logs: LogPaths) -> Transcripts:
    """Read sample transcripts from eval logs.

    Args:
        logs: Log paths as file(s) or directories.

    Returns:
        Transcripts: Collection of transcripts for scanning.
    """
    return EvalLogTranscripts(logs)


async def transcripts_from_snapshot(snapshot: ScanTranscripts) -> Transcripts:
    match snapshot.type:
        case "eval_log":
            return EvalLogTranscripts(snapshot)
        case _:
            raise ValueError(f"Unrecognized transcript type '{snapshot.type}")


async def transcripts_df_from_snapshot(snapshot: ScanTranscripts) -> pd.DataFrame:
    """Get a DataFrame from a transcript snapshot (internal use with original column names)."""
    match snapshot.type:
        case "eval_log":
            return EvalLogTranscripts._logs_df_from_snapshot(snapshot)
        case _:
            raise ValueError(f"Unrecognized transcript type '{snapshot.type}")


async def transcripts_df_for_results(snapshot: ScanTranscripts) -> pd.DataFrame:
    """Get a DataFrame from a transcript snapshot with renamed columns.

    Renames columns to match scanner table naming for easier joins:
    - sample_id => id (matches scanner's transcript_id)
    - eval_id => source_id (matches scanner's transcript_source_id)
    - log => source_uri (matches scanner's transcript_source_uri)
    """
    match snapshot.type:
        case "eval_log":
            df = EvalLogTranscripts._logs_df_from_snapshot(snapshot)

            # Rename columns for consistency with scanner tables
            rename_map = {
                "sample_id": "id",
                "eval_id": "source_id",
                "log": "source_uri",
            }
            return df.rename(columns=rename_map)
        case _:
            raise ValueError(f"Unrecognized transcript type '{snapshot.type}")


TranscriptColumns: list[Column] = (
    EvalId
    + EvalLogPath
    + [
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
