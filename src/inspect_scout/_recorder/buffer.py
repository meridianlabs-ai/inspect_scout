import json
import os
import shutil
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Final, Sequence, Set, TypeVar, cast

import anyio
import jsonlines
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
from inspect_ai._util.appdirs import inspect_data_dir
from inspect_ai._util.file import file
from inspect_ai._util.hash import mm3_hash
from inspect_ai.scorer import value_to_float
from pydantic import JsonValue
from upath import UPath

from inspect_scout._recorder.summary import Summary
from inspect_scout._util.path import normalize_for_hashing

from .._scanner.result import Error, ResultReport
from .._scanspec import ScanSpec
from .._transcript.types import TranscriptInfo
from .._transcript.util import LazyJSONDict

SCAN_ERRORS = "_errors.jsonl"
SCAN_SUMMARY = "_summary.json"


# Per-buffer-dir in-process state. Multiple `RecorderBuffer` instances
# targeting the same buffer dir (e.g. inspect_ai's eval_set scans samples
# concurrently, each via its own ephemeral `FileRecorder`) share both the
# lock and the live `Summary`. Mutating the shared `Summary` under the
# lock and persisting it directly (without re-reading disk) keeps the
# read-modify-write race-free while avoiding a disk round-trip per call.
@dataclass
class _BufferState:
    lock: anyio.Lock
    summary: Summary | None = None


_buffer_states: dict[str, _BufferState] = {}


def _buffer_state(buffer_dir: UPath) -> _BufferState:
    key = buffer_dir.as_posix()
    state = _buffer_states.get(key)
    if state is None:
        state = _BufferState(lock=anyio.Lock())
        _buffer_states[key] = state
    return state


def _invalidate_buffer_state(buffer_dir: UPath) -> None:
    """Drop the cached `_BufferState` for `buffer_dir`.

    The next buffer attached to this dir then re-reads `_summary.json`
    from disk. Called when external code mutates buffer-dir contents
    out-of-band (e.g. `cleanup_buffer_dir`).
    """
    _buffer_states.pop(buffer_dir.as_posix(), None)


class RecorderBuffer:
    """
    Parquet-backed buffer compatible with the previous RecorderBuffer API.

    Layout on disk:
      <scanbuffer_dir> / "<hash_of_scan_location>" /
          scanner=<scanner_name> /
              <transcript_id>.parquet

    Assumptions:
      - transcript_id is a UUID (safe as filename)
      - only one process writes a given <transcript_id>.parquet once
    """

    @staticmethod
    def buffer_dir(scan_location: str) -> UPath:
        env = os.getenv("SCOUT_SCANBUFFER_DIR")
        scan_buffer_dir = UPath(
            os.path.expanduser(env) if env else inspect_data_dir("scout_scanbuffer")
        )
        normalized = normalize_for_hashing(scan_location)
        return scan_buffer_dir / f"{mm3_hash(normalized)}"

    def __init__(
        self,
        scan_location: str,
        spec: ScanSpec,
        *,
        pool_dedup: bool = True,
    ):
        """Initialize a buffer attached to `scan_location`.

        This is purely a passive constructor: it reads existing buffer state
        from disk or creates fresh files only if they don't exist. Mode-
        specific setup (clearing for a fresh scan, truncating errors for a
        retry-resume, preserving errors for a continuation) is the caller's
        responsibility — see `FileRecorder.init` / `resume` / `attach`.

        The in-memory `Summary` is shared via `_buffer_state` across every
        `RecorderBuffer` constructed for the same buffer dir in this
        process, so concurrent ephemeral instances see each other's
        updates without re-reading `_summary.json` from disk on every
        record.
        """
        self._buffer_dir = RecorderBuffer.buffer_dir(scan_location)
        self._buffer_dir.mkdir(parents=True, exist_ok=True)
        self._spec = spec
        self._pool_dedup = pool_dedup

        self._state = _buffer_state(self._buffer_dir)
        if self._state.summary is None:
            # first attach to this buffer dir in-process — populate the
            # shared `Summary` from disk, or create + persist a fresh one
            scan_summary_file = self._buffer_dir.joinpath(SCAN_SUMMARY)
            if scan_summary_file.exists():
                self._state.summary = read_scan_summary(self._buffer_dir, spec)
            else:
                self._state.summary = Summary(
                    complete=False, scanners=list(spec.scanners.keys())
                )
                with open(scan_summary_file.as_posix(), "w") as f:
                    f.write(self._state.summary.model_dump_json(indent=2))

        self._error_file = self._buffer_dir.joinpath(SCAN_ERRORS)

    async def record(
        self,
        transcript: TranscriptInfo,
        scanner: str,
        results: Sequence[ResultReport],
        metrics: dict[str, dict[str, float]] | None,
    ) -> None:
        import pyarrow.parquet as pq

        # do some bridging for inspect logs
        m = transcript.metadata
        transcript_date = resolve_metadata_var(transcript.date, "eval_created", m)
        transcript_task_set = resolve_metadata_var(transcript.task_set, "task_name", m)
        transcript_task_id = resolve_metadata_var(transcript.task_id, "id", m)
        transcript_task_repeat = resolve_metadata_var(
            transcript.task_repeat, "epoch", m
        )
        transcript_agent = resolve_metadata_var(transcript.agent, "solver", m)
        transcript_agent_args = resolve_metadata_var(
            transcript.agent_args, "solver_args", m
        )
        transcript_model = resolve_metadata_var(transcript.model, "model", m)
        transcript_model_options = resolve_metadata_var(
            transcript.model_options, "generate_config", m
        )
        transcript_score = resolve_metadata_var(transcript.score, "score", m)
        transcript_success = resolve_success_value(
            transcript.success, cast(JsonValue | None, transcript_score)
        )
        transcript_message_count = resolve_metadata_var(
            transcript.message_count, "message_count", m
        )
        transcript_total_time = resolve_metadata_var(
            transcript.total_time, "total_time", m
        )
        transcript_total_tokens = resolve_metadata_var(
            transcript.total_tokens, "total_tokens", m
        )
        transcript_error = resolve_metadata_var(transcript.error, "error", m)
        transcript_limit = resolve_metadata_var(transcript.limit, "limit", m)

        records = [
            cast(
                dict[str, str | bool | int | float | None],
                {
                    "transcript_id": transcript.transcript_id,
                    "transcript_source_type": transcript.source_type,
                    "transcript_source_id": transcript.source_id,
                    "transcript_source_uri": transcript.source_uri,
                    "transcript_date": transcript_date,
                    "transcript_task_set": transcript_task_set,
                    "transcript_task_id": transcript_task_id,
                    "transcript_task_repeat": transcript_task_repeat,
                    "transcript_agent": transcript_agent,
                    "transcript_agent_args": transcript_agent_args,
                    "transcript_model": transcript_model,
                    "transcript_model_options": transcript_model_options,
                    "transcript_score": transcript_score,
                    "transcript_success": transcript_success,
                    "transcript_message_count": transcript_message_count,
                    "transcript_total_time": transcript_total_time,
                    "transcript_total_tokens": transcript_total_tokens,
                    "transcript_error": transcript_error,
                    "transcript_limit": transcript_limit,
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
            | result.to_df_columns(pool_dedup=self._pool_dedup)
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

        # update and persist summary. the shared in-memory `Summary` is
        # the source of truth; the lock serializes mutation + write so
        # concurrent buffer instances against this buffer dir don't lose
        # updates and never observe a partial state on disk.
        async with self._state.lock:
            assert self._state.summary is not None  # set in __init__
            self._state.summary._report(transcript, scanner, results, metrics)
            with open(self._buffer_dir.joinpath(SCAN_SUMMARY).as_posix(), "w") as f:
                f.write(self._state.summary.model_dump_json(indent=2))

        # record errors (open(..., "at") gives OS-atomic appends)
        for result in results:
            if result.error is not None:
                with open(str(self._error_file), "at") as f:
                    f.write(result.error.model_dump_json(warnings=False) + "\n")

    async def record_metrics(
        self,
        scanner: str,
        metrics: dict[str, dict[str, float]] | None,
    ) -> None:
        async with self._state.lock:
            assert self._state.summary is not None  # set in __init__
            self._state.summary._report_metrics(scanner, metrics)
            with open(self._buffer_dir.joinpath(SCAN_SUMMARY).as_posix(), "w") as f:
                f.write(self._state.summary.model_dump_json(indent=2))

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
        assert self._state.summary is not None  # set in __init__
        return self._state.summary

    def cleanup(self) -> None:
        """Remove the buffer directory for this scan (best-effort)."""
        cleanup_buffer_dir(self._buffer_dir)


T = TypeVar("T")


def resolve_metadata_var(
    value: T | None, metadata_key: str, metadata: dict[str, Any]
) -> T | None:
    if value is None:
        return metadata.get(metadata_key, None)
    else:
        return value


def resolve_success_value(value: bool | None, score: JsonValue | None) -> bool | None:
    if value is not None:
        return value  # Use explicit value when provided
    else:
        # Fall back to computing from score
        if isinstance(score, str | int | float | bool):
            return value_to_float()(score) > 0
        else:
            return None


def scanner_table(
    buffer_dir: UPath,
    scanner: str,
    *,
    extra_inputs: list[UPath] | None = None,
) -> bytes | None:
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

    # resolve input paths: the per-transcript buffer dir, plus any extra
    # parquets to merge in (e.g. the previously compacted output from an
    # earlier sync, so multi-call resume retains prior rows even after
    # the buffer is cleaned). pyarrow's ds.dataset(list) requires uniform
    # types in the list, so we expand the directory to its parquet files.
    #
    # The buffer's per-transcript file is named `<transcript_id>.parquet`
    # and is authoritative for that transcript_id: any rows for the same
    # transcript_id in `extra_inputs` (a previously-compacted output that
    # was built from an earlier copy of these same buffer files) are
    # duplicates and must be filtered out — otherwise rows double-count
    # when `sync` runs more than once without clearing the buffer between
    # calls (e.g. an `eval_set` resume cycle where `complete=False`).
    sdir = buffer_dir / f"scanner={_sanitize_component(scanner)}"
    buffer_inputs: list[str] = []
    buffer_tids: list[str] = []
    if sdir.exists():
        for p in sdir.glob("*.parquet"):
            buffer_inputs.append(str(p))
            buffer_tids.append(p.stem)
    extra_paths: list[str] = (
        [p.as_posix() for p in extra_inputs if p.exists()] if extra_inputs else []
    )
    inputs = buffer_inputs + extra_paths
    if not inputs:
        # avoid creating a schema-less empty parquet when there's nothing to
        # compact. If you *must* emit a file in that case, you need a known
        # schema.
        return None
    # set of paths whose batches need transcript_id filtering against
    # `buffer_tids` (paths NOT in the buffer dir → from extra_inputs)
    extra_paths_set: set[str] = set(extra_paths)
    buffer_tid_array: pa.Array[Any] | None = (
        pa.array(buffer_tids, type=pa.string()) if buffer_tids else None
    )

    # build dataset
    dataset: ds.Dataset = ds.dataset(inputs, format="parquet")

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
    # 2. Force 'value' and 'transcript_score' columns to string since they can have
    #    mixed types across different result reports / transcripts
    corrected_fields = []
    for field in schema:
        if pa.types.is_null(field.type):
            # Promote null type to string
            corrected_fields.append(pa.field(field.name, pa.string(), nullable=True))
        elif field.name in {"value", "transcript_score"}:
            # Force mixed-type columns to string
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
        # batches from `extra_inputs` get filtered against buffer_tids
        # so a transcript represented in the buffer doesn't double-count
        is_extra = fragment.path in extra_paths_set
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

            # drop rows whose transcript_id is already covered by a
            # buffer file (the buffer is authoritative for those tids)
            if is_extra and buffer_tid_array is not None:
                mask = pc.invert(
                    pc.is_in(batch.column("transcript_id"), value_set=buffer_tid_array)
                )
                batch = batch.filter(mask)
                if batch.num_rows == 0:
                    continue

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
    # drop the in-process shared `_BufferState` so a future buffer for
    # this dir re-reads disk instead of keeping stale `Summary` state
    _invalidate_buffer_state(buffer_dir)


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

    # Build arrays column-wise so string columns can use large_string offsets.
    # This avoids the ~2GB limit of Arrow's default string offset type.
    columns: list[str] = []
    seen_columns: set[str] = set()
    for record in norm:
        for key in record:
            if key not in seen_columns:
                seen_columns.add(key)
                columns.append(key)

    arrays: dict[str, pa.Array[Any]] = {}
    for column in columns:
        values = [record.get(column) for record in norm]
        non_null_values = [value for value in values if value is not None]
        if non_null_values and all(isinstance(value, str) for value in non_null_values):
            arrays[column] = pa.array(values, type=pa.large_string())
        else:
            arrays[column] = pa.array(values)

    return pa.table(arrays)


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
