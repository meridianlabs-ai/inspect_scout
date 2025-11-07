import io
from typing import Literal, Sequence

import duckdb
import pandas as pd
from inspect_ai._util.asyncfiles import AsyncFilesystem
from inspect_ai._util.file import file, filesystem
from inspect_ai._util.json import to_json_str_safe
from typing_extensions import override
from upath import UPath

from inspect_scout._recorder.summary import Summary

from .._recorder.buffer import (
    SCAN_ERRORS,
    SCAN_SUMMARY,
    RecorderBuffer,
    cleanup_buffer_dir,
    read_scan_errors,
    read_scan_summary,
    scanner_table,
)
from .._scanner.result import Error, ResultReport
from .._scanspec import ScanSpec
from .._transcript.types import TranscriptInfo
from .recorder import (
    ScanRecorder,
    ScanResultsDB,
    ScanResultsDF,
    Status,
)

SCAN_JSON = "_scan.json"


class FileRecorder(ScanRecorder):
    def __init__(self) -> None:
        self._scan_dir: UPath | None = None
        self._scan_spec: ScanSpec | None = None

    @override
    async def init(self, spec: ScanSpec, scans_location: str) -> None:
        # create the scan dir
        self._scan_dir = _ensure_scan_dir(UPath(scans_location), spec.scan_id)
        self._scanners_completed: list[str] = []
        # write the spec
        with file((self.scan_dir / SCAN_JSON).as_posix(), "w") as f:
            f.write(to_json_str_safe(spec))
        # save the spec
        self._scan_spec = spec

        # create the scan buffer
        self._scan_buffer = RecorderBuffer(self._scan_dir.as_posix(), self._scan_spec)

    @override
    async def resume(self, scan_location: str) -> ScanSpec:
        self._scan_dir = UPath(scan_location)
        self._scanners_completed = [
            scanner.as_posix() for scanner in self._scan_dir.glob("*.parquet")
        ]
        self._scan_fs = filesystem(self._scan_dir.as_posix())
        self._scan_spec = _read_scan_spec(self._scan_dir)
        self._scan_buffer = RecorderBuffer(self._scan_dir.as_posix(), self.scan_spec)
        return self._scan_spec

    @override
    async def location(self) -> str:
        return self.scan_dir.as_posix()

    @override
    async def is_recorded(self, transcript: TranscriptInfo, scanner: str) -> bool:
        # if we either already have a final scanner file or this transcript
        # is in the buffer without errors then the scan is recorded
        if _scanner_parquet_file(self.scan_dir, scanner) in self._scanners_completed:
            return True
        else:
            return await self._scan_buffer.is_recorded(transcript, scanner)

    @override
    async def record(
        self, transcript: TranscriptInfo, scanner: str, results: Sequence[ResultReport]
    ) -> None:
        await self._scan_buffer.record(transcript, scanner, results)

    @override
    async def flush(self) -> None:
        pass

    @override
    async def errors(self) -> list[Error]:
        return self._scan_buffer.errors()

    @override
    async def summary(self) -> Summary:
        return self._scan_buffer.scan_summary().model_copy(deep=True)

    @property
    def scan_dir(self) -> UPath:
        if self._scan_dir is None:
            raise RuntimeError(
                "File recorder must be initialized or resumed before use."
            )
        return self._scan_dir

    @property
    def scan_spec(self) -> ScanSpec:
        if self._scan_spec is None:
            raise RuntimeError(
                "File recorder must be initialized or resumed before use."
            )
        return self._scan_spec

    @override
    @staticmethod
    async def sync_status(scan_location: str) -> None:
        # get state
        scan_dir = UPath(scan_location)
        scan_spec = _read_scan_spec(scan_dir)
        scan_buffer_dir = RecorderBuffer.buffer_dir(scan_location)

        # sync summary and errors
        _sync_status_files(scan_dir, scan_buffer_dir, scan_spec)

    @override
    @staticmethod
    async def complete(scan_location: str) -> Status:
        # get state
        scan_dir = UPath(scan_location)
        scan_spec = _read_scan_spec(scan_dir)
        scan_buffer_dir = RecorderBuffer.buffer_dir(scan_location)

        # write scanners
        async with AsyncFilesystem() as fs:
            for scanner in sorted(scan_spec.scanners.keys()):
                parquet_bytes = scanner_table(scan_buffer_dir, scanner)
                if parquet_bytes is not None:
                    await fs.write_file(
                        _scanner_parquet_file(scan_dir, scanner), parquet_bytes
                    )

        # sync summary and errors
        _sync_status_files(scan_dir, scan_buffer_dir, scan_spec)

        # cleanup scan buffer
        cleanup_buffer_dir(scan_buffer_dir)

        return Status(
            complete=True,
            spec=scan_spec,
            location=scan_dir.as_posix(),
            summary=read_scan_summary(scan_dir, scan_spec),
            errors=_read_scan_errors(scan_dir),
        )

    @override
    @staticmethod
    async def status(scan_location: str) -> Status:
        buffer_dir = RecorderBuffer.buffer_dir(scan_location)
        spec = _read_scan_spec(UPath(scan_location))
        return Status(
            complete=False if buffer_dir.exists() else True,
            spec=spec,
            location=scan_location,
            summary=read_scan_summary(buffer_dir, spec)
            if buffer_dir.exists()
            else read_scan_summary(UPath(scan_location), spec),
            errors=_read_scan_errors(buffer_dir)
            if buffer_dir.exists()
            else _read_scan_errors(UPath(scan_location)),
        )

    @override
    @staticmethod
    async def results(
        scan_location: str,
        *,
        scanner: str | None = None,
    ) -> ScanResultsDF:
        import pyarrow.parquet as pq
        from upath import UPath

        scan_dir = UPath(scan_location)
        status = await FileRecorder.status(scan_location)

        async with AsyncFilesystem() as fs:

            async def scanner_df(parquet_file: UPath) -> pd.DataFrame:
                # read table into df
                bytes = await fs.read_file(parquet_file.as_posix())
                table = pq.read_table(io.BytesIO(bytes))
                df = table.to_pandas(types_mapper=pd.ArrowDtype)

                # cast value column to appropriate type based on value_type
                df = _cast_value_column(df)

                # return
                return df

            # read data
            scanners: dict[str, pd.DataFrame] = {}

            # single scanner
            if scanner is not None:
                parquet_file = scan_dir / f"{scanner}.parquet"
                scanners[scanner] = await scanner_df(parquet_file)

            # all scanners
            else:
                for parquet_file in sorted(scan_dir.glob("*.parquet")):
                    name = parquet_file.stem
                    scanners[name] = await scanner_df(parquet_file)

            return ScanResultsDF(
                status=status.complete,
                spec=status.spec,
                location=status.location,
                summary=status.summary,
                errors=status.errors,
                scanners=scanners,
            )

    @override
    @staticmethod
    async def results_db(
        scan_location: str, *, rows: Literal["results", "transcripts"] = "results"
    ) -> ScanResultsDB:
        from upath import UPath

        scan_dir = UPath(scan_location)
        status = await FileRecorder.status(scan_location)

        # Create in-memory DuckDB connection
        conn = duckdb.connect(":memory:")

        # Create views for each parquet file
        for parquet_file in sorted(scan_dir.glob("*.parquet")):
            scanner_name = parquet_file.stem
            # Create a view that references the parquet file
            # Use absolute path to ensure it works regardless of working directory
            abs_path = parquet_file.resolve().as_posix()

            # Check if we need to expand resultsets
            if rows == "results" and _has_resultsets(conn, abs_path):
                # Create expanded view with UNNEST for resultset rows
                sql = _create_expanded_view_sql(conn, abs_path, scanner_name)
                conn.execute(sql)
            else:
                # Use existing simple view logic (for transcripts mode or non-resultset scanners)
                # Check if value_type is uniform and needs casting
                uniform_type = _get_uniform_value_type(conn, abs_path)
                if uniform_type in ("boolean", "number"):
                    cast_expr = _cast_value_sql(uniform_type)
                    select_clause = f"SELECT * REPLACE ({cast_expr} AS value)"
                else:
                    select_clause = "SELECT *"

                conn.execute(
                    f"CREATE VIEW {scanner_name} AS {select_clause} FROM read_parquet('{abs_path}')"
                )

        return ScanResultsDB(
            status=status.complete,
            spec=status.spec,
            location=status.location,
            summary=status.summary,
            errors=status.errors,
            conn=conn,
        )

    @override
    @staticmethod
    async def list(scans_location: str) -> list[Status]:
        scans_dir = UPath(scans_location)
        return [
            await FileRecorder.status(scan_dir.as_posix())
            for scan_dir in scans_dir.rglob("scan_id=*")
        ]


def _scanner_parquet_file(scan_dir: UPath, scanner: str) -> str:
    return (scan_dir / f"{scanner}.parquet").as_posix()


def _read_scan_spec(scan_dir: UPath) -> ScanSpec:
    scan_json = scan_dir / SCAN_JSON
    fs = filesystem(scan_dir.as_posix())
    if not fs.exists(scan_json.as_posix()):
        raise RuntimeError(
            f"The specified directory '{scan_dir}' does not contain a scan."
        )

    with file(scan_json.as_posix(), "r") as f:
        return ScanSpec.model_validate_json(f.read())


def _read_scan_errors(scan_dir: UPath) -> list[Error]:
    scan_errors = scan_dir / SCAN_ERRORS
    return read_scan_errors(str(scan_errors))


def _find_scan_dir(scans_path: UPath, scan_id: str) -> UPath | None:
    _ensure_scans_dir(scans_path)
    for f in scans_path.glob(f"scan_id={scan_id}"):
        if f.is_dir():
            return f

    return None


def _ensure_scan_dir(scans_path: UPath, scan_id: str) -> UPath:
    # look for an existing scan dir
    scan_dir = _find_scan_dir(scans_path, scan_id)

    # if there is no scan_dir then create one
    if scan_dir is None:
        scan_dir = scans_path / f"scan_id={scan_id}"
        scan_dir.mkdir(parents=True, exist_ok=False)

    # return scan dir
    return scan_dir


def _ensure_scans_dir(scans_dir: UPath) -> None:
    scans_dir.mkdir(parents=True, exist_ok=True)


def _has_resultsets(conn: duckdb.DuckDBPyConnection, parquet_path: str) -> bool:
    """
    Check if a parquet file contains any resultset rows.

    Args:
        conn: DuckDB connection
        parquet_path: Path to the parquet file

    Returns:
        True if any rows have value_type == 'resultset', False otherwise
    """
    result = conn.execute(
        f"SELECT COUNT(*) FROM read_parquet('{parquet_path}') WHERE value_type = 'resultset' LIMIT 1"
    ).fetchone()
    return result is not None and result[0] > 0


def _create_expanded_view_sql(
    conn: duckdb.DuckDBPyConnection, parquet_path: str, scanner_name: str
) -> str:
    """
    Generate SQL to create an expanded view that unnests resultset rows.

    For rows where value_type == 'resultset', the value field contains a JSON array
    of Result objects. This function generates SQL that:
    1. Passes through non-resultset rows as-is
    2. Unnests resultset rows using json_extract and UNNEST
    3. Extracts Result fields into columns
    4. Applies type casting to the value column

    Args:
        conn: DuckDB connection to query schema
        parquet_path: Path to the parquet file
        scanner_name: Name for the view

    Returns:
        SQL CREATE VIEW statement with UNION of non-resultset and expanded resultset rows
    """
    # Query the actual column names from the parquet file to avoid hardcoding
    # We use LIMIT 0 to get just the schema without reading data
    result = conn.execute(
        f"SELECT * FROM read_parquet('{parquet_path}') LIMIT 0"
    ).description
    all_columns = [col[0] for col in result]

    # These are the Result fields that need special handling during expansion
    result_fields = {
        "uuid",
        "label",
        "value",
        "value_type",
        "answer",
        "explanation",
        "metadata",
    }

    # These columns should be NULL in expanded rows to avoid incorrect aggregation
    # (they represent the scan execution, not individual results)
    scan_execution_fields = {"scan_total_tokens", "scan_model_usage"}

    # Build the non-resultset rows query with explicit column selection
    non_resultset_cols = ", ".join(all_columns)
    non_resultset_query = f"""
    SELECT {non_resultset_cols} FROM read_parquet('{parquet_path}')
    WHERE value_type != 'resultset' OR value_type IS NULL
    """

    # Build the expanded resultset rows query
    # Base columns are everything except the result fields and scan execution fields
    base_columns = [
        col
        for col in all_columns
        if col not in result_fields and col not in scan_execution_fields
    ]

    # Type casting expression for the extracted value
    # elem will be a JSON string from UNNEST, need to cast it first
    cast_value_expr = """CASE
            WHEN COALESCE(json_extract_string(CAST(elem AS JSON), '$.type'), 'null') = 'boolean'
            THEN CASE
                WHEN json_extract_string(CAST(elem AS JSON), '$.value') IN ('true', 'True') THEN TRUE
                WHEN json_extract_string(CAST(elem AS JSON), '$.value') IN ('false', 'False') THEN FALSE
                ELSE NULL
            END
            WHEN COALESCE(json_extract_string(CAST(elem AS JSON), '$.type'), 'null') = 'number'
            THEN TRY_CAST(json_extract_string(CAST(elem AS JSON), '$.value') AS DOUBLE)
            ELSE json_extract(CAST(elem AS JSON), '$.value')
        END"""

    # Build column selects for expanded query in the same order as all_columns
    expanded_col_selects = []
    for col in all_columns:
        if col in base_columns:
            # Base columns from the parquet table
            expanded_col_selects.append(f"r.{col}")
        elif col in scan_execution_fields:
            # NULL out scan execution fields to avoid incorrect aggregation
            expanded_col_selects.append(f"NULL AS {col}")
        elif col == "uuid":
            expanded_col_selects.append(
                "json_extract_string(CAST(elem AS JSON), '$.uuid') AS uuid"
            )
        elif col == "label":
            expanded_col_selects.append(
                "json_extract_string(CAST(elem AS JSON), '$.label') AS label"
            )
        elif col == "value":
            expanded_col_selects.append(f"({cast_value_expr}) AS value")
        elif col == "value_type":
            expanded_col_selects.append(
                "COALESCE(json_extract_string(CAST(elem AS JSON), '$.type'), 'null') AS value_type"
            )
        elif col == "answer":
            expanded_col_selects.append(
                "json_extract_string(CAST(elem AS JSON), '$.answer') AS answer"
            )
        elif col == "explanation":
            expanded_col_selects.append(
                "json_extract_string(CAST(elem AS JSON), '$.explanation') AS explanation"
            )
        elif col == "metadata":
            expanded_col_selects.append(
                "COALESCE(json_extract_string(CAST(elem AS JSON), '$.metadata'), '{{}}') AS metadata"
            )

    expanded_resultset_query = f"""
    SELECT
        {", ".join(expanded_col_selects)}
    FROM read_parquet('{parquet_path}') r,
    UNNEST(CAST(json_extract(r.value, '$') AS JSON[])) AS t(elem)
    WHERE r.value_type = 'resultset'
    """

    # Combine both queries with UNION ALL
    return f"""CREATE VIEW {scanner_name} AS
    SELECT * FROM (
        {non_resultset_query}
        UNION ALL
        {expanded_resultset_query}
    )"""


def _get_uniform_value_type(
    conn: duckdb.DuckDBPyConnection, parquet_path: str
) -> str | None:
    """
    Check if value_type is uniform across all rows in a parquet file.

    Args:
        conn: DuckDB connection
        parquet_path: Path to the parquet file

    Returns:
        The uniform value_type if all rows have the same type, None otherwise
    """
    result = conn.execute(
        f"SELECT DISTINCT value_type FROM read_parquet('{parquet_path}') WHERE value_type IS NOT NULL"
    ).fetchall()

    if len(result) == 1:
        return str(result[0][0])
    else:
        return None


def _cast_value_sql(value_type: str) -> str:
    """
    Generate SQL CASE expression to cast the value column based on value_type.

    Args:
        value_type: The uniform value type ('boolean', 'number', etc.)

    Returns:
        SQL CASE expression for casting the value column
    """
    if value_type == "boolean":
        return """CASE
            WHEN value IN ('true', 'True') THEN TRUE
            WHEN value IN ('false', 'False') THEN FALSE
            ELSE NULL
        END"""
    elif value_type == "number":
        return "TRY_CAST(value AS DOUBLE)"
    else:
        # For string, null, array, object - keep as-is
        return "value"


def _cast_value_column(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cast the 'value' column to its appropriate type based on 'value_type'.

    The value column is stored as string in parquet files to handle mixed types
    during compaction. This function restores the original types for analysis.

    Args:
        df: DataFrame with 'value' and 'value_type' columns

    Returns:
        DataFrame with value column cast to appropriate type
    """
    if "value" not in df.columns or "value_type" not in df.columns:
        return df

    # Check if value_type is uniform across all rows
    value_types = df["value_type"].dropna().unique()

    if len(value_types) == 0:
        # No value_type information, keep as-is
        return df
    elif len(value_types) == 1:
        # Uniform type - safe to cast entire column
        vtype = value_types[0]

        try:
            if vtype == "boolean":
                # Handle various string representations of booleans
                df["value"] = df["value"].map(
                    {
                        "true": True,
                        "false": False,
                        "True": True,
                        "False": False,
                        None: None,
                    }
                )
            elif vtype == "number":
                # Use nullable Int64/Float64 to preserve NaN
                # Try int first, fall back to float
                df["value"] = pd.to_numeric(df["value"], errors="coerce")
            elif vtype in ("string", "null"):
                # Already strings or nulls, keep as-is
                pass
            elif vtype in ("array", "object"):
                # Complex types are JSON strings, keep as-is
                # Could optionally parse JSON here if needed
                pass
        except Exception:
            # If casting fails for any reason, keep original string representation
            pass
    else:
        # Mixed types - keep as strings for safety
        pass

    return df


def _sync_status_files(
    scan_dir: UPath, scan_buffer_dir: UPath, scan_spec: ScanSpec
) -> None:
    """Copy summary and errors from buffer to scan directory."""
    # copy scan summary
    with file((scan_dir / SCAN_SUMMARY).as_posix(), "w") as f:
        f.write(read_scan_summary(scan_buffer_dir, scan_spec).model_dump_json())

    # copy errors
    with file((scan_dir / SCAN_ERRORS).as_posix(), "w") as f:
        for error in _read_scan_errors(scan_buffer_dir):
            f.write(error.model_dump_json(warnings=False) + "\n")
