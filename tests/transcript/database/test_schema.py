"""Tests for transcript database schema module."""

import json
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from inspect_scout._transcript.database.schema import (
    TRANSCRIPT_SCHEMA_FIELDS,
    SchemaField,
    TranscriptSchemaError,
    generate_schema_table_markdown,
    reserved_columns,
    transcripts_db_schema,
    validate_transcript_schema,
)


class TestTranscriptSchemaFields:
    """Tests for TRANSCRIPT_SCHEMA_FIELDS definition."""

    def test_has_transcript_id_as_first_field(self) -> None:
        """First field should be transcript_id."""
        assert TRANSCRIPT_SCHEMA_FIELDS[0].name == "transcript_id"

    def test_transcript_id_is_required(self) -> None:
        """transcript_id should be the only required field."""
        required = [f for f in TRANSCRIPT_SCHEMA_FIELDS if f.required]
        assert len(required) == 1
        assert required[0].name == "transcript_id"

    def test_has_all_expected_fields(self) -> None:
        """Schema should have all expected standard fields."""
        field_names = {f.name for f in TRANSCRIPT_SCHEMA_FIELDS}
        expected = {
            "transcript_id",
            "source_type",
            "source_id",
            "source_uri",
            "date",
            "task_set",
            "task_id",
            "task_repeat",
            "agent",
            "agent_args",
            "model",
            "model_options",
            "score",
            "success",
            "message_count",
            "total_time",
            "total_tokens",
            "error",
            "limit",
            "messages",
            "events",
            "timelines",
        }
        assert field_names == expected

    def test_json_serialized_fields(self) -> None:
        """Correct fields are marked as JSON-serialized."""
        json_fields = {f.name for f in TRANSCRIPT_SCHEMA_FIELDS if f.json_serialized}
        expected = {
            "agent_args",
            "model_options",
            "score",
            "messages",
            "events",
            "timelines",
        }
        assert json_fields == expected

    def test_all_fields_have_descriptions(self) -> None:
        """All fields should have non-empty descriptions."""
        for field in TRANSCRIPT_SCHEMA_FIELDS:
            assert field.description, f"Field {field.name} has no description"

    def test_field_types(self) -> None:
        """Fields should have correct PyArrow types."""
        field_map = {f.name: f for f in TRANSCRIPT_SCHEMA_FIELDS}

        # String fields
        string_fields = [
            "transcript_id",
            "source_type",
            "source_id",
            "source_uri",
            "date",
            "task_set",
            "task_id",
            "agent",
            "agent_args",
            "model",
            "model_options",
            "score",
            "error",
            "limit",
            "messages",
            "events",
        ]
        for name in string_fields:
            assert field_map[name].pyarrow_type == pa.string(), (
                f"{name} should be string"
            )

        # Integer fields
        assert field_map["task_repeat"].pyarrow_type == pa.int64()
        assert field_map["total_tokens"].pyarrow_type == pa.int64()
        assert field_map["message_count"].pyarrow_type == pa.int64()

        # Float fields
        assert field_map["total_time"].pyarrow_type == pa.float64()

        # Boolean fields
        assert field_map["success"].pyarrow_type == pa.bool_()


class TestTranscriptsDbSchema:
    """Tests for transcripts_db_schema function."""

    def test_pyarrow_format(self) -> None:
        """transcripts_db_schema('pyarrow') returns valid PyArrow Schema."""
        schema = transcripts_db_schema(format="pyarrow")
        assert isinstance(schema, pa.Schema)
        assert len(schema) == 22
        assert "transcript_id" in schema.names

    def test_pyarrow_field_types(self) -> None:
        """PyArrow schema has correct field types."""
        schema = transcripts_db_schema(format="pyarrow")
        assert schema.field("transcript_id").type == pa.string()
        assert schema.field("task_repeat").type == pa.int64()
        assert schema.field("total_time").type == pa.float64()
        assert schema.field("success").type == pa.bool_()

    def test_avro_format(self) -> None:
        """transcripts_db_schema('avro') returns valid Avro schema dict."""
        schema = transcripts_db_schema(format="avro")
        assert isinstance(schema, dict)
        assert schema["type"] == "record"
        assert schema["name"] == "Transcript"
        assert "fields" in schema
        assert len(schema["fields"]) == 22

    def test_avro_field_structure(self) -> None:
        """Avro schema fields have correct structure."""
        schema = transcripts_db_schema(format="avro")
        fields = {f["name"]: f for f in schema["fields"]}

        # Required field (transcript_id)
        assert fields["transcript_id"]["type"] == "string"

        # Optional string field
        assert fields["source_type"]["type"] == ["null", "string"]

        # Optional int field
        assert fields["task_repeat"]["type"] == ["null", "long"]

        # Optional float field
        assert fields["total_time"]["type"] == ["null", "double"]

        # Optional bool field
        assert fields["success"]["type"] == ["null", "boolean"]

    def test_avro_is_json_serializable(self) -> None:
        """Avro schema can be serialized to JSON."""
        schema = transcripts_db_schema(format="avro")
        json_str = json.dumps(schema)
        parsed = json.loads(json_str)
        assert parsed == schema

    def test_json_format(self) -> None:
        """transcripts_db_schema('json') returns valid JSON Schema dict."""
        schema = transcripts_db_schema(format="json")
        assert isinstance(schema, dict)
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert schema["type"] == "object"
        assert "properties" in schema
        assert "required" in schema
        assert "transcript_id" in schema["required"]

    def test_json_schema_properties(self) -> None:
        """JSON Schema has correct property types."""
        schema = transcripts_db_schema(format="json")
        props = schema["properties"]

        assert props["transcript_id"]["type"] == "string"
        assert props["task_repeat"]["type"] == "integer"
        assert props["total_time"]["type"] == "number"
        assert props["success"]["type"] == "boolean"

    def test_pandas_format(self) -> None:
        """transcripts_db_schema('pandas') returns empty DataFrame."""
        df = transcripts_db_schema(format="pandas")
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0
        assert len(df.columns) == 22

    def test_pandas_column_dtypes(self) -> None:
        """Pandas DataFrame has correct column dtypes."""
        df = transcripts_db_schema(format="pandas")
        assert df["transcript_id"].dtype == "object"  # string
        assert df["task_repeat"].dtype == "Int64"  # nullable int
        assert df["total_time"].dtype == "float64"
        assert df["success"].dtype == "boolean"  # nullable bool

    def test_invalid_format_raises(self) -> None:
        """Invalid format raises ValueError."""
        with pytest.raises(ValueError, match="Unknown format"):
            transcripts_db_schema(format="invalid")  # type: ignore


class TestReservedColumns:
    """Tests for reserved_columns function."""

    def test_returns_set(self) -> None:
        """Should return a set."""
        result = reserved_columns()
        assert isinstance(result, set)

    def test_contains_all_schema_fields(self) -> None:
        """Should contain all schema field names."""
        reserved = reserved_columns()
        for field in TRANSCRIPT_SCHEMA_FIELDS:
            assert field.name in reserved

    def test_contains_filename(self) -> None:
        """Should contain 'filename' (internal DuckDB column)."""
        reserved = reserved_columns()
        assert "filename" in reserved

    def test_count(self) -> None:
        """Should have correct count (22 schema fields + filename)."""
        reserved = reserved_columns()
        assert len(reserved) == 23


class TestValidateTranscriptSchema:
    """Tests for validate_transcript_schema function."""

    def test_valid_schema_passes(self) -> None:
        """Valid schema with all required fields passes validation."""
        schema = pa.schema(
            [
                ("transcript_id", pa.string()),
                ("source_type", pa.string()),
                ("messages", pa.string()),
            ]
        )
        errors = validate_transcript_schema(schema)
        assert len(errors) == 0

    def test_missing_required_field(self) -> None:
        """Missing transcript_id fails validation."""
        schema = pa.schema(
            [
                ("source_type", pa.string()),
                ("messages", pa.string()),
            ]
        )
        errors = validate_transcript_schema(schema)
        assert len(errors) == 1
        assert errors[0].field == "transcript_id"
        assert errors[0].error_type == "missing_required"

    def test_wrong_type_for_string_field(self) -> None:
        """Wrong type for string field fails validation."""
        schema = pa.schema(
            [
                ("transcript_id", pa.int64()),  # Should be string
            ]
        )
        errors = validate_transcript_schema(schema)
        assert len(errors) == 1
        assert errors[0].field == "transcript_id"
        assert errors[0].error_type == "wrong_type"

    def test_large_string_allowed(self) -> None:
        """large_string type is allowed for string fields."""
        schema = pa.schema(
            [
                ("transcript_id", pa.large_string()),
                ("messages", pa.large_string()),
            ]
        )
        errors = validate_transcript_schema(schema)
        assert len(errors) == 0

    def test_wrong_type_for_bool_field(self) -> None:
        """Wrong type for bool field fails validation."""
        schema = pa.schema(
            [
                ("transcript_id", pa.string()),
                ("success", pa.string()),  # Should be bool
            ]
        )
        errors = validate_transcript_schema(schema)
        assert len(errors) == 1
        assert errors[0].field == "success"
        assert errors[0].error_type == "wrong_type"

    def test_wrong_type_for_int_field(self) -> None:
        """Wrong type for int field fails validation."""
        schema = pa.schema(
            [
                ("transcript_id", pa.string()),
                ("total_tokens", pa.string()),  # Should be int
            ]
        )
        errors = validate_transcript_schema(schema)
        assert len(errors) == 1
        assert errors[0].field == "total_tokens"
        assert errors[0].error_type == "wrong_type"

    def test_any_integer_type_allowed(self) -> None:
        """Any integer type is allowed for int fields."""
        fields: list[pa.Field[pa.DataType]] = [
            pa.field("transcript_id", pa.string()),
            pa.field("total_tokens", pa.int32()),  # int32 instead of int64
            pa.field("task_repeat", pa.uint64()),  # unsigned
        ]
        schema = pa.schema(fields)
        errors = validate_transcript_schema(schema)
        assert len(errors) == 0

    def test_any_float_type_allowed(self) -> None:
        """Any floating type is allowed for float fields."""
        fields: list[pa.Field[pa.DataType]] = [
            pa.field("transcript_id", pa.string()),
            pa.field("total_time", pa.float32()),  # float32 instead of float64
        ]
        schema = pa.schema(fields)
        errors = validate_transcript_schema(schema)
        assert len(errors) == 0

    def test_validate_from_parquet_file(self, tmp_path: Path) -> None:
        """Can validate schema from a Parquet file path."""
        # Create a valid parquet file
        table = pa.table(
            {
                "transcript_id": ["t1", "t2"],
                "messages": ["[]", "[]"],
            }
        )
        path = tmp_path / "valid.parquet"
        pq.write_table(table, str(path))

        errors = validate_transcript_schema(str(path))
        assert len(errors) == 0

    def test_validate_from_pyarrow_table(self) -> None:
        """Can validate schema from a PyArrow Table."""
        table = pa.table(
            {
                "transcript_id": ["t1", "t2"],
                "messages": ["[]", "[]"],
            }
        )
        errors = validate_transcript_schema(table)
        assert len(errors) == 0

    def test_validate_from_directory(self, tmp_path: Path) -> None:
        """Can validate schema from a directory containing Parquet files."""
        # Create a valid parquet file in directory
        table = pa.table(
            {
                "transcript_id": ["t1", "t2"],
                "messages": ["[]", "[]"],
            }
        )
        path = tmp_path / "valid.parquet"
        pq.write_table(table, str(path))

        errors = validate_transcript_schema(tmp_path)
        assert len(errors) == 0

    def test_validate_empty_directory(self, tmp_path: Path) -> None:
        """Empty directory returns error."""
        errors = validate_transcript_schema(tmp_path)
        assert len(errors) == 1
        assert "No parquet files found" in errors[0].message


class TestGenerateSchemaTableMarkdown:
    """Tests for generate_schema_table_markdown function."""

    def test_returns_string(self) -> None:
        """Should return a string."""
        result = generate_schema_table_markdown()
        assert isinstance(result, str)

    def test_has_header_row(self) -> None:
        """Should have markdown table header."""
        result = generate_schema_table_markdown()
        assert "| Field | Type | Description |" in result

    def test_has_separator_row(self) -> None:
        """Should have separator row."""
        result = generate_schema_table_markdown()
        assert "|-------|------|-------------|" in result

    def test_has_all_fields(self) -> None:
        """Should include all schema fields."""
        result = generate_schema_table_markdown()
        for field in TRANSCRIPT_SCHEMA_FIELDS:
            if field.name == "timelines":
                continue
            assert f"`{field.name}`" in result

    def test_transcript_id_marked_required(self) -> None:
        """transcript_id should be marked as Required."""
        result = generate_schema_table_markdown()
        # Find the line with transcript_id
        lines = result.split("\n")
        transcript_id_line = next(line for line in lines if "`transcript_id`" in line)
        assert "Required." in transcript_id_line

    def test_optional_fields_marked_optional(self) -> None:
        """Optional fields should be marked as Optional."""
        result = generate_schema_table_markdown()
        lines = result.split("\n")
        source_type_line = next(line for line in lines if "`source_type`" in line)
        assert "Optional." in source_type_line

    def test_json_fields_have_json_suffix(self) -> None:
        """JSON-serialized fields should have (JSON) in type column."""
        result = generate_schema_table_markdown()
        lines = result.split("\n")
        messages_line = next(line for line in lines if "`messages`" in line)
        assert "(JSON)" in messages_line


class TestSchemaField:
    """Tests for SchemaField dataclass."""

    def test_create_basic(self) -> None:
        """Can create a basic SchemaField."""
        field = SchemaField(
            name="test_field",
            pyarrow_type=pa.string(),
            required=True,
            description="A test field",
        )
        assert field.name == "test_field"
        assert field.pyarrow_type == pa.string()
        assert field.required is True
        assert field.description == "A test field"
        assert field.json_serialized is False  # default

    def test_create_with_json_serialized(self) -> None:
        """Can create SchemaField with json_serialized=True."""
        field = SchemaField(
            name="json_field",
            pyarrow_type=pa.string(),
            required=False,
            description="A JSON field",
            json_serialized=True,
        )
        assert field.json_serialized is True


class TestTranscriptSchemaError:
    """Tests for TranscriptSchemaError dataclass."""

    def test_create_error(self) -> None:
        """Can create a TranscriptSchemaError."""
        error = TranscriptSchemaError(
            field="test_field",
            error_type="wrong_type",
            message="Expected string, got int",
        )
        assert error.field == "test_field"
        assert error.error_type == "wrong_type"
        assert error.message == "Expected string, got int"

    def test_error_types(self) -> None:
        """Error types are constrained to valid values."""
        # These should work
        TranscriptSchemaError(field="f", error_type="missing_required", message="m")
        TranscriptSchemaError(field="f", error_type="wrong_type", message="m")
        TranscriptSchemaError(field="f", error_type="reserved_conflict", message="m")


# --- Regression Tests ---
# These tests ensure the schema refactoring doesn't break existing functionality


class TestSchemaMetadataSeparation:
    """Tests ensuring schema module correctly governs metadata separation."""

    def test_reserved_columns_matches_schema_fields(self) -> None:
        schema_names = {f.name for f in TRANSCRIPT_SCHEMA_FIELDS}
        expected = schema_names | {"filename"}
        assert reserved_columns() == expected

    def test_metadata_validation_rejects_reserved_names(self) -> None:
        """_validate_metadata_keys should reject all reserved column names."""
        from inspect_scout._transcript.database.parquet.transcripts import (
            _validate_metadata_keys,
        )

        for col_name in reserved_columns():
            if col_name == "filename":
                continue  # Not a user-facing column
            with pytest.raises(ValueError, match="reserved"):
                _validate_metadata_keys({col_name: "test"})

    def test_similar_but_different_metadata_keys_allowed(self) -> None:
        """Metadata keys similar to reserved names but different should work."""
        from inspect_scout._transcript.database.parquet.transcripts import (
            _validate_metadata_keys,
        )

        # These are similar but NOT reserved
        _validate_metadata_keys(
            {
                "task_id_custom": "ok",
                "model_name": "ok",
                "agent_type": "ok",
            }
        )  # Should not raise


class TestSchemaDuckDBConsistency:
    """Tests ensuring schema types work correctly with DuckDB."""

    def test_pyarrow_schema_creates_valid_parquet(self, tmp_path: Path) -> None:
        """Schema from transcripts_db_schema('pyarrow') creates valid parquet."""
        schema = transcripts_db_schema(format="pyarrow")

        # Create table with schema, writing null values
        arrays = {f.name: pa.nulls(1, type=f.type) for f in schema}
        table = pa.table(arrays, schema=schema)

        path = tmp_path / "test.parquet"
        pq.write_table(table, str(path))

        # Should be readable
        read_table = pq.read_table(str(path))
        assert read_table.schema.names == schema.names

    def test_all_schema_fields_have_valid_duckdb_types(self) -> None:
        """Every schema field should have a valid DuckDB type mapping."""
        from inspect_scout._transcript.database.parquet.transcripts import (
            _pyarrow_to_duckdb_type,
        )

        for field in TRANSCRIPT_SCHEMA_FIELDS:
            # Should not raise
            duckdb_type = _pyarrow_to_duckdb_type(field.pyarrow_type)
            assert duckdb_type in {"VARCHAR", "BIGINT", "DOUBLE", "BOOLEAN"}


class TestSchemaRoundTrip:
    """Integration tests for schema-based database creation."""

    @pytest.mark.asyncio
    async def test_schema_created_parquet_queryable(self, tmp_path: Path) -> None:
        """Parquet created with exported schema should be queryable via API."""
        from inspect_scout._query import Query
        from inspect_scout._transcript.database.parquet.transcripts import (
            ParquetTranscriptsDB,
        )

        schema = transcripts_db_schema(format="pyarrow")

        # Create minimal valid data with transcript_id and messages
        # Then add null columns for all other fields
        data: dict[str, Any] = {
            "transcript_id": ["test-1", "test-2"],
            "messages": ["[]", "[]"],
        }
        for field in schema:
            if field.name not in data:
                data[field.name] = pa.nulls(2, type=field.type)

        table = pa.table(data, schema=schema)

        db_path = tmp_path / "test_db"
        db_path.mkdir()
        pq.write_table(table, str(db_path / "data.parquet"))

        # Should be queryable via ParquetTranscriptsDB
        db = ParquetTranscriptsDB(str(db_path))
        await db.connect()
        try:
            count = await db.count(Query())
            assert count == 2
        finally:
            await db.disconnect()
