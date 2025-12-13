import json
import os
import shutil
from datetime import datetime
from typing import Any, Final, Sequence, Set, cast

import jsonlines
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
from inspect_ai._util.appdirs import inspect_data_dir
from inspect_ai._util.file import file
from inspect_ai._util.hash import mm3_hash
from upath import UPath

from inspect_scout._recorder.summary import Summary
from inspect_scout._util.path import normalize_for_hashing

from .._scanner.result import Error, ResultReport
from .._scanspec import ScanSpec
from .._transcript.types import TranscriptInfo
from .._transcript.util import LazyJSONDict

SCAN_ERRORS = "_errors.jsonl"
SCAN_SUMMARY = "_summary.json"


class RecorderBuffer:
    """
    Parquet-backed buffer compatible with the previous RecorderBuffer API.

    Layout on disk:
      inspect_data_dir("scout_scanbuffer") / "<hash_of_scan_location>" /
          scanner=<scanner_name> /
              <transcript_id>.parquet

    Assumptions:
      - transcript_id is a UUID (safe as filename)
      - only one process writes a given <transcript_id>.parquet once
    """

    @staticmethod
    def buffer_dir(scan_location: str) -> UPath:
        normalized = normalize_for_hashing(scan_location)
        return UPath(inspect_data_dir("scout_scanbuffer") / f"{mm3_hash(normalized)}")

    def __init__(self, scan_location: str, spec: ScanSpec):
        self._buffer_dir = RecorderBuffer.buffer_dir(scan_location)
        self._buffer_dir.mkdir(parents=True, exist_ok=True)
        self._spec = spec

        # establish scan summary if required
        scan_summary_file = self._buffer_dir.joinpath(SCAN_SUMMARY)
        if not scan_summary_file.exists():
            self._scan_summary = Summary(
                complete=False, scanners=list(spec.scanners.keys())
            )
            with open(scan_summary_file.as_posix(), "w") as f:
                f.write(self._scan_summary.model_dump_json(indent=2))
        else:
            self._scan_summary = read_scan_summary(self._buffer_dir, spec)

        # truncate errors
        self._error_file = self._buffer_dir.joinpath(SCAN_ERRORS)
        with self._error_file.open("w"):
            pass  # truncates existing file

    async def record(
        self,
        transcript: TranscriptInfo,
        scanner: str,
        results: Sequence[ResultReport],
        metrics: dict[str, dict[str, float]] | None,
    ) -> None:
        import pyarrow.parquet as pq

        records = [
            cast(
                dict[str, str | bool | int | float | None],
                {
                    "transcript_id": transcript.transcript_id,
                    "transcript_source_type": transcript.source_type,
                    "transcript_source_id": transcript.source_id,
                    "transcript_source_uri": transcript.source_uri,
                    "transcript_metadata": transcript.metadata,
                    "scan_id": self._spec.scan_id,
                    "scan_tags": self._spec.tags or [],
                    "scan_metadata": self._spec.metadata or {},
                    "scan_git_origin": self._spec.revision.origin
                    if self._spec.revision
                    else None,
                    "scan_git_version": self._spec.revision.version
                    if self._spec.revision
                    else None,
                    "scan_git_commit": self._spec.revision.commit
                    if self._spec.revision
                    else None,
                    "scanner_key": scanner,
                    "scanner_name": self._spec.scanners[scanner].name,
                    "scanner_version": self._spec.scanners[scanner].version,
                    "scanner_package_version": self._spec.scanners[
                        scanner
                    ].package_version,
                    "scanner_file": self._spec.scanners[scanner].file,
                    "scanner_params": self._spec.scanners[scanner].params,
                },
            )
            | result.to_df_columns()
            | {"timestamp": datetime.now().astimezone().isoformat()}
            for result in results
        ]
        if not records:
            return

        table = _records_to_arrow(records)

        # Ensure destination directory exists
        sdir = self._buffer_dir / f"scanner={_sanitize_component(scanner)}"
        sdir.mkdir(parents=True, exist_ok=True)

        # One-shot write per transcript
        final_path = sdir / f"{transcript.transcript_id}.parquet"

        # Atomic write: write to .tmp, then os.replace to final
        tmp_path = sdir / f".{transcript.transcript_id}.parquet.tmp"
        pq.write_table(
            table,
            tmp_path.as_posix(),
            compression="zstd",
            use_dictionary=True,
        )
        os.replace(tmp_path.as_posix(), final_path.as_posix())

        # update and write summary
        self._scan_summary._report(transcript, scanner, results, metrics)
        with open(self._buffer_dir.joinpath(SCAN_SUMMARY).as_posix(), "w") as f:
            f.write(self._scan_summary.model_dump_json(indent=2))

        # record errors
        for result in results:
            if result.error is not None:
                with open(str(self._error_file), "at") as f:
                    f.write(result.error.model_dump_json(warnings=False) + "\n")

    async def record_metrics(
        self,
        scanner: str,
        metrics: dict[str, dict[str, float]] | None,
    ) -> None:
        # update and write summary
        self._scan_summary._report_metrics(scanner, metrics)
        with open(self._buffer_dir.joinpath(SCAN_SUMMARY).as_posix(), "w") as f:
            f.write(self._scan_summary.model_dump_json(indent=2))

    async def is_recorded(self, transcript_id: str, scanner: str) -> bool:
        sdir = self._buffer_dir / f"scanner={_sanitize_component(scanner)}"
        transcript_file = sdir / f"{transcript_id}.parquet"
        if transcript_file.exists():
            # check if there are any non-null scan_error fields
            table = pq.read_table(transcript_file.as_posix(), columns=["scan_error"])
            scan_errors = table.column("scan_error")
            if pc.any(pc.is_valid(scan_errors)).as_py():
                return False
            return True
        else:
            return False

    def errors(self) -> list[Error]:
        return read_scan_errors(str(self._error_file))

    def scan_summary(self) -> Summary:
        return self._scan_summary

    def cleanup(self) -> None:
        """Remove the buffer directory for this scan (best-effort)."""
        cleanup_buffer_dir(self._buffer_dir)


def scanner_table(buffer_dir: UPath, scanner: str) -> bytes | None:
    import pyarrow as pa
    import pyarrow.dataset as ds
    import pyarrow.parquet as pq

    # NOTE: this function attempts to cap memory usage at ~ 100MB for compacting
    # scanner results. It does get a bit fancy/complicated and uses a bunch of
    # pyarrow streaming primitives. If this ends up working out poorly the naive
    # implementation is just this:
    #
    #   dataset = ds.dataset(sdir.as_posix(), format="parquet")
    #   table = dataset.to_table() # materialize fully
    #
    #   pq.write_table(
    #       table,
    #       table_file,
    #       compression="zstd",
    #       use_dictionary=True,
    #   )

    MAX_BYTES: Final[int] = 100_000_000
    DEFAULT_BATCH_ROWS: Final[int] = 1_000

    # resolve input dir
    sdir = buffer_dir / f"scanner={_sanitize_component(scanner)}"
    if not sdir.exists():
        # we avoid creating a schema-less empty Parquet when there is no dataset at all.
        # If you *must* emit a file even when the directory is missing, you need a known schema.
        return None

    # build dataset
    dataset: ds.Dataset = ds.dataset(str(sdir), format="parquet")

    # discover the unified schema up-front. This ensures column order/types are stable.
    # if there are absolutely no fragments under sdir, accessing .schema may raise.
    try:
        schema: pa.Schema = dataset.schema
    except Exception as e:
        raise RuntimeError(
            f"Unable to discover dataset schema under {sdir}: {e}"
        ) from e

    # Correct schema to handle type inconsistencies across files:
    # 1. Promote null-type columns to string (unknown type)
    # 2. Force 'value' column to string since it can have mixed types (bool, int, float, str)
    #    across different result reports
    corrected_fields = []
    for field in schema:
        if pa.types.is_null(field.type):
            # Promote null type to string
            corrected_fields.append(pa.field(field.name, pa.string(), nullable=True))
        elif field.name == "value":
            # Force value column to string to handle mixed types
            corrected_fields.append(pa.field(field.name, pa.string(), nullable=True))
        else:
            corrected_fields.append(field)
    schema = pa.schema(corrected_fields)

    # state for bounded accumulation -> large-ish row groups
    accumulated: list[pa.RecordBatch] = []
    accumulated_bytes: int = 0

    def flush_accumulated(writer: pq.ParquetWriter) -> None:
        nonlocal accumulated, accumulated_bytes
        if not accumulated:
            return
        table = pa.Table.from_batches(accumulated)  # bounded by MAX_BYTES
        writer.write_table(table)
        accumulated.clear()
        accumulated_bytes = 0

    # Create an in-memory buffer (use PyArrow's native type for efficiency)
    buffer = pa.BufferOutputStream()
    writer = pq.ParquetWriter(
        buffer,
        schema,
        compression="zstd",
        use_dictionary=True,
    )

    # iterate materialized batches; to keep memory in check we use a small batch_size.
    # We iterate fragments and manually cast to handle schema inconsistencies
    for fragment in dataset.get_fragments():
        for batch in fragment.to_batches(
            batch_size=DEFAULT_BATCH_ROWS,
            use_threads=False,
        ):
            # Cast batch to corrected schema to handle type mismatches
            # (e.g., null columns promoted to string, or missing columns)
            try:
                arrays = []
                for field in schema:
                    if field.name in batch.schema.names:
                        # Column exists - cast it to target type
                        col = batch.column(field.name)
                        arrays.append(col.cast(field.type))
                    else:
                        # Column missing - create null array
                        arrays.append(pa.array([None] * len(batch), type=field.type))

                batch = pa.RecordBatch.from_arrays(arrays, schema=schema)
            except Exception as e:
                raise RuntimeError(f"Failed to cast batch to schema: {e}") from e

            size = batch.nbytes
            if accumulated_bytes and accumulated_bytes + size > MAX_BYTES:
                flush_accumulated(writer)
            accumulated.append(batch)
            accumulated_bytes += size

    # Final flush. If no rows were seen, this still leaves us with an empty file (schema only).
    flush_accumulated(writer)
    writer.close()

    # TODO: If we changed the signature of this function from:
    #   bytes | None
    #     to
    #   pa.Buffer | None
    # We could avoid the copy (that to_pybytes does) altogether.
    # Keep in mind that the previous BytesIO.getvalue() made a copy too.
    return buffer.getvalue().to_pybytes()


def cleanup_buffer_dir(buffer_dir: UPath) -> None:
    try:
        shutil.rmtree(buffer_dir.as_posix(), ignore_errors=True)
    except Exception:
        pass


def _sanitize_component(name: str) -> str:
    """Make a string safe for use as a single path component."""
    import re

    # allow [A-Za-z0-9 _-+=.,@]; replace others with "_"
    return re.sub(r"[^a-zA-Z0-9_\-=+.,@]", "_", name)


def _normalize_scalar(v: Any) -> Any:
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    if isinstance(v, (str, int, float)):
        return v
    # datetime/date
    try:
        from datetime import date, datetime

        if isinstance(v, (datetime, date)):
            return v
    except Exception:
        pass
    # Handle LazyJSONDict specially to avoid materializing unparsed fields
    if isinstance(v, LazyJSONDict):
        return v.to_json_string()
    # Decimal, lists, dicts, sets, tuples -> JSON text if possible
    try:
        return json.dumps(v, ensure_ascii=False, separators=(",", ":"))
    except Exception:
        return str(v)


def _records_to_arrow(records: list[dict[str, Any]]) -> "pa.Table":
    """Build an Arrow table directly from normalized Python records."""
    import pyarrow as pa

    # First normalize scalars
    norm = [{k: _normalize_scalar(v) for k, v in r.items()} for r in records]

    # Check for mixed-type columns and convert them to strings
    if norm:
        # Detect which columns have mixed types
        columns_types: dict[str, Set[Any]] = {}
        for record in norm:
            for key, value in record.items():
                if value is not None:
                    val_type = type(value).__name__
                    if key not in columns_types:
                        columns_types[key] = set()
                    columns_types[key].add(val_type)

        # Convert mixed-type columns to strings
        mixed_cols = {k for k, types in columns_types.items() if len(types) > 1}
        if mixed_cols:
            for record in norm:
                for col in mixed_cols:
                    if col in record and record[col] is not None:
                        record[col] = str(record[col])

    return pa.Table.from_pylist(norm)


def read_scan_errors(error_file: str) -> list[Error]:
    try:
        with file(error_file, "r") as f:
            errors: list[Error] = []
            reader = jsonlines.Reader(f)
            for error in reader.iter(type=dict):
                errors.append(Error(**error))
            return errors
    except FileNotFoundError:
        return []


def read_scan_summary(scan_dir: UPath, spec: ScanSpec) -> Summary:
    try:
        scan_summary = scan_dir.joinpath(SCAN_SUMMARY)
        with file(scan_summary.as_posix(), "r") as f:
            summary = f.read().strip()
            if summary:
                return Summary.model_validate_json(summary)
            else:
                return Summary(complete=False, scanners=list(spec.scanners.keys()))
    except FileNotFoundError:
        return Summary(complete=False, scanners=list(spec.scanners.keys()))
