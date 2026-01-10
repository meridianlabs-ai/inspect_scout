"""Transcript database schema definition and utilities.

This module provides a single source of truth for the transcript database schema,
with functions to export the schema in various formats.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, overload

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq


@dataclass
class SchemaField:
    """Definition of a transcript database field."""

    name: str
    """Column name."""

    pyarrow_type: pa.DataType
    """PyArrow data type for the column."""

    required: bool
    """Whether the field is required."""

    description: str
    """Human-readable description."""

    json_serialized: bool = False
    """Whether the field is stored as a JSON string."""


# Schema field definitions in canonical order (matches documentation)
TRANSCRIPT_SCHEMA_FIELDS: list[SchemaField] = [
    SchemaField(
        name="transcript_id",
        pyarrow_type=pa.string(),
        required=True,
        description="A globally unique identifier for a transcript.",
    ),
    SchemaField(
        name="source_type",
        pyarrow_type=pa.string(),
        required=False,
        description='Type of transcript source (e.g. "weave", "logfire", "eval_log", etc.). Useful for providing a hint to readers about what might be available in the `metadata` field.',
    ),
    SchemaField(
        name="source_id",
        pyarrow_type=pa.string(),
        required=False,
        description="Globally unique identifier for a transcript source (e.g. a project id).",
    ),
    SchemaField(
        name="source_uri",
        pyarrow_type=pa.string(),
        required=False,
        description="URI for source data (e.g. link to a web page or REST resource for discovering more about the transcript).",
    ),
    SchemaField(
        name="date",
        pyarrow_type=pa.string(),
        required=False,
        description="ISO 8601 datetime of transcript creation.",
    ),
    SchemaField(
        name="task_set",
        pyarrow_type=pa.string(),
        required=False,
        description="Set from which transcript task was drawn (e.g. Inspect task name or benchmark name).",
    ),
    SchemaField(
        name="task_id",
        pyarrow_type=pa.string(),
        required=False,
        description="Identifier for task (e.g. dataset sample id).",
    ),
    SchemaField(
        name="task_repeat",
        pyarrow_type=pa.int64(),
        required=False,
        description="Repeat for a given task id within a task set (e.g. epoch).",
    ),
    SchemaField(
        name="agent",
        pyarrow_type=pa.string(),
        required=False,
        description="Agent used to execute task.",
    ),
    SchemaField(
        name="agent_args",
        pyarrow_type=pa.string(),
        required=False,
        description="Arguments passed to create agent.",
        json_serialized=True,
    ),
    SchemaField(
        name="model",
        pyarrow_type=pa.string(),
        required=False,
        description="Main model used by agent.",
    ),
    SchemaField(
        name="model_options",
        pyarrow_type=pa.string(),
        required=False,
        description="Generation options for main model.",
        json_serialized=True,
    ),
    SchemaField(
        name="score",
        pyarrow_type=pa.string(),
        required=False,
        description="Value indicating score on task.",
        json_serialized=True,
    ),
    SchemaField(
        name="success",
        pyarrow_type=pa.bool_(),
        required=False,
        description="Boolean reduction of `score` to succeeded/failed.",
    ),
    SchemaField(
        name="total_time",
        pyarrow_type=pa.float64(),
        required=False,
        description="Time (in seconds) required to execute task.",
    ),
    SchemaField(
        name="total_tokens",
        pyarrow_type=pa.int64(),
        required=False,
        description="Tokens spent in execution of task.",
    ),
    SchemaField(
        name="error",
        pyarrow_type=pa.string(),
        required=False,
        description="Error message that terminated the task.",
    ),
    SchemaField(
        name="limit",
        pyarrow_type=pa.string(),
        required=False,
        description='Limit that caused the task to exit (e.g. "tokens", "messages", etc.).',
    ),
    SchemaField(
        name="messages",
        pyarrow_type=pa.string(),
        required=False,
        description="List of ChatMessage with message history.",
        json_serialized=True,
    ),
    SchemaField(
        name="events",
        pyarrow_type=pa.string(),
        required=False,
        description="List of Event with event history (e.g. model events, tool events, etc.).",
        json_serialized=True,
    ),
]


# --- Public API ---


@overload
def transcripts_db_schema(format: Literal["pyarrow"]) -> pa.Schema: ...


@overload
def transcripts_db_schema(format: Literal["avro"]) -> dict[str, Any]: ...


@overload
def transcripts_db_schema(format: Literal["json"]) -> dict[str, Any]: ...


@overload
def transcripts_db_schema(format: Literal["pandas"]) -> pd.DataFrame: ...


def transcripts_db_schema(
    format: Literal["pyarrow", "avro", "json", "pandas"] = "pyarrow",
) -> pa.Schema | dict[str, Any] | pd.DataFrame:
    """Get transcript database schema in various formats.

    Args:
        format: Output format:
            - "pyarrow": PyArrow Schema for creating Parquet files
            - "avro": Avro schema as dict (JSON-serializable)
            - "json": JSON Schema as dict
            - "pandas": Empty DataFrame with correct dtypes

    Returns:
        Schema in the requested format.
    """
    if format == "pyarrow":
        return _to_pyarrow_schema()
    elif format == "avro":
        return _to_avro_schema()
    elif format == "json":
        return _to_json_schema()
    elif format == "pandas":
        return _to_pandas_dataframe()
    else:
        raise ValueError(f"Unknown format: {format}")


# --- Internal Functions ---


def reserved_columns() -> set[str]:
    """Get set of reserved column names.

    These are the standard schema fields that cannot be used as metadata keys.
    """
    reserved = {field.name for field in TRANSCRIPT_SCHEMA_FIELDS}
    # Also include 'filename' which is used internally by DuckDB
    reserved.add("filename")
    return reserved


@dataclass
class TranscriptSchemaError:
    """Schema validation error."""

    field: str
    """Field name that has the error."""

    error_type: Literal["missing_required", "wrong_type", "reserved_conflict"]
    """Type of error."""

    message: str
    """Human-readable error message."""


def validate_transcript_schema(
    source: str | Path | pa.Table | pa.Schema,
) -> list[TranscriptSchemaError]:
    """Validate a parquet file, table, or schema against transcript schema.

    Args:
        source: Path to parquet file/directory, PyArrow Table, or Schema.

    Returns:
        List of schema errors (empty if valid).
    """
    errors: list[TranscriptSchemaError] = []

    # Get schema from source
    if isinstance(source, pa.Schema):
        schema = source
    elif isinstance(source, pa.Table):
        schema = source.schema
    else:
        # Read schema from parquet file
        path = Path(source)
        if path.is_dir():
            # Find first parquet file
            parquet_files = list(path.glob("*.parquet"))
            if not parquet_files:
                return [
                    TranscriptSchemaError(
                        field="",
                        error_type="missing_required",
                        message=f"No parquet files found in {path}",
                    )
                ]
            path = parquet_files[0]
        schema = pq.read_schema(path)

    # Get column names from schema
    column_names = set(schema.names)

    # Check required fields
    for field in TRANSCRIPT_SCHEMA_FIELDS:
        if field.required and field.name not in column_names:
            errors.append(
                TranscriptSchemaError(
                    field=field.name,
                    error_type="missing_required",
                    message=f"Required field '{field.name}' is missing",
                )
            )

    # Check field types for present fields
    for field in TRANSCRIPT_SCHEMA_FIELDS:
        if field.name not in column_names:
            continue

        actual_type = schema.field(field.name).type
        expected_type = field.pyarrow_type

        # String columns: allow large_string as equivalent
        if expected_type == pa.string():
            if actual_type not in (pa.string(), pa.large_string()):
                errors.append(
                    TranscriptSchemaError(
                        field=field.name,
                        error_type="wrong_type",
                        message=f"Field '{field.name}' has type {actual_type}, expected string",
                    )
                )
        # Boolean columns
        elif expected_type == pa.bool_():
            if actual_type != pa.bool_():
                errors.append(
                    TranscriptSchemaError(
                        field=field.name,
                        error_type="wrong_type",
                        message=f"Field '{field.name}' has type {actual_type}, expected bool",
                    )
                )
        # Float columns: allow any floating type
        elif expected_type == pa.float64():
            if not pa.types.is_floating(actual_type):
                errors.append(
                    TranscriptSchemaError(
                        field=field.name,
                        error_type="wrong_type",
                        message=f"Field '{field.name}' has type {actual_type}, expected float",
                    )
                )
        # Integer columns: allow any integer type
        elif expected_type == pa.int64():
            if not pa.types.is_integer(actual_type):
                errors.append(
                    TranscriptSchemaError(
                        field=field.name,
                        error_type="wrong_type",
                        message=f"Field '{field.name}' has type {actual_type}, expected integer",
                    )
                )

    return errors


def generate_schema_table_markdown() -> str:
    """Generate markdown table of schema fields for documentation.

    Returns:
        Markdown-formatted table string.
    """
    # Build table rows
    rows: list[list[str]] = []
    for field in TRANSCRIPT_SCHEMA_FIELDS:
        # Field name with backticks
        name = f"`{field.name}`"

        # Type with JSON annotation
        type_str = _pyarrow_type_to_display(field.pyarrow_type)
        if field.json_serialized:
            type_str += " (JSON)"

        # Description with Required/Optional prefix
        prefix = "Required." if field.required else "Optional."
        description = f"{prefix} {field.description}"

        rows.append([name, type_str, description])

    # Generate markdown table
    header = "| Field | Type | Description |"
    separator = "|-------|------|-------------|"
    body_rows = [f"| {' | '.join(row)} |" for row in rows]

    return "\n".join([header, separator] + body_rows)


# --- Schema Conversion Helpers ---


def _to_pyarrow_schema() -> pa.Schema:
    """Convert schema fields to PyArrow Schema."""
    fields = [(f.name, f.pyarrow_type) for f in TRANSCRIPT_SCHEMA_FIELDS]
    return pa.schema(fields)


def _to_avro_schema() -> dict[str, Any]:
    """Convert schema fields to Avro schema dict."""
    avro_fields = []
    for field in TRANSCRIPT_SCHEMA_FIELDS:
        avro_type = _pyarrow_to_avro_type(
            field.pyarrow_type, nullable=not field.required
        )
        avro_field: dict[str, Any] = {
            "name": field.name,
            "type": avro_type,
        }
        if field.description:
            avro_field["doc"] = field.description
        avro_fields.append(avro_field)

    return {
        "type": "record",
        "name": "Transcript",
        "namespace": "inspect_scout.transcript",
        "doc": "Transcript database record schema",
        "fields": avro_fields,
    }


def _to_json_schema() -> dict[str, Any]:
    """Convert schema fields to JSON Schema dict."""
    properties: dict[str, Any] = {}
    required_fields: list[str] = []

    for field in TRANSCRIPT_SCHEMA_FIELDS:
        json_type = _pyarrow_to_json_type(field.pyarrow_type)
        prop: dict[str, Any] = {
            "type": json_type,
            "description": field.description,
        }
        properties[field.name] = prop

        if field.required:
            required_fields.append(field.name)

    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Transcript",
        "description": "Transcript database record schema",
        "type": "object",
        "properties": properties,
        "required": required_fields,
    }


def _to_pandas_dataframe() -> pd.DataFrame:
    """Create empty DataFrame with correct schema."""
    # Build column dict with correct dtypes
    columns: dict[str, Any] = {}
    for field in TRANSCRIPT_SCHEMA_FIELDS:
        dtype = _pyarrow_to_pandas_dtype(field.pyarrow_type)
        columns[field.name] = pd.Series([], dtype=dtype)

    return pd.DataFrame(columns)


def _pyarrow_to_avro_type(pa_type: pa.DataType, nullable: bool = True) -> Any:
    """Map PyArrow type to Avro type."""
    type_map: dict[pa.DataType, str] = {
        pa.string(): "string",
        pa.int64(): "long",
        pa.int32(): "int",
        pa.float64(): "double",
        pa.float32(): "float",
        pa.bool_(): "boolean",
    }

    avro_type = type_map.get(pa_type, "string")

    if nullable:
        return ["null", avro_type]
    return avro_type


def _pyarrow_to_json_type(pa_type: pa.DataType) -> str:
    """Map PyArrow type to JSON Schema type."""
    if pa_type == pa.string():
        return "string"
    elif pa_type in (pa.int64(), pa.int32()):
        return "integer"
    elif pa_type in (pa.float64(), pa.float32()):
        return "number"
    elif pa_type == pa.bool_():
        return "boolean"
    else:
        return "string"


def _pyarrow_to_pandas_dtype(pa_type: pa.DataType) -> str:
    """Map PyArrow type to pandas dtype string."""
    if pa_type == pa.string():
        return "object"
    elif pa_type == pa.int64():
        return "Int64"  # Nullable integer
    elif pa_type == pa.int32():
        return "Int32"
    elif pa_type == pa.float64():
        return "float64"
    elif pa_type == pa.float32():
        return "float32"
    elif pa_type == pa.bool_():
        return "boolean"  # Nullable boolean
    else:
        return "object"


def _pyarrow_type_to_display(pa_type: pa.DataType) -> str:
    """Convert PyArrow type to human-readable display string."""
    type_map: dict[pa.DataType, str] = {
        pa.string(): "string",
        pa.int64(): "int64",
        pa.int32(): "int32",
        pa.float64(): "float64",
        pa.float32(): "float32",
        pa.bool_(): "bool",
    }
    return type_map.get(pa_type, str(pa_type))
