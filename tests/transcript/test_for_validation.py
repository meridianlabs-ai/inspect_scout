"""Tests for Transcripts.for_validation() method."""

from inspect_scout._transcript.transcripts import Transcripts
from inspect_scout._validation import Validation, ValidationCase


class MockTranscripts(Transcripts):
    """Mock implementation of Transcripts for testing."""

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return None

    async def count(self) -> int:
        return 0

    async def index(self):
        return iter([])

    async def _read(self, transcript, content):
        raise NotImplementedError()

    async def snapshot(self):
        raise NotImplementedError()


def test_for_validation_single_id():
    """Test for_validation with a single ID."""
    validation = Validation(
        cases=[
            ValidationCase(id="transcript_1", target=True),
            ValidationCase(id="transcript_2", target=False),
        ]
    )

    transcripts = MockTranscripts()
    filtered = transcripts.for_validation(validation)

    # Verify a condition was added
    assert len(filtered._where) == 1

    # Verify the SQL generated
    condition = filtered._where[0]
    sql, params = condition.to_sql("sqlite")

    assert sql == '"sample_id" IN (?, ?)'
    assert params == ["transcript_1", "transcript_2"]


def test_for_validation_list_ids():
    """Test for_validation with list IDs."""
    validation = Validation(
        cases=[
            ValidationCase(id=["transcript_1", "transcript_2"], target=True),
            ValidationCase(id="transcript_3", target=False),
        ]
    )

    transcripts = MockTranscripts()
    filtered = transcripts.for_validation(validation)

    assert len(filtered._where) == 1

    condition = filtered._where[0]
    sql, params = condition.to_sql("sqlite")

    assert sql == '"sample_id" IN (?, ?, ?)'
    assert params == ["transcript_1", "transcript_2", "transcript_3"]


def test_for_validation_mixed_ids():
    """Test for_validation with mixed single and list IDs."""
    validation = Validation(
        cases=[
            ValidationCase(id="transcript_1", target=True),
            ValidationCase(id=["transcript_2", "transcript_3"], target=False),
            ValidationCase(id="transcript_4", target=True),
        ]
    )

    transcripts = MockTranscripts()
    filtered = transcripts.for_validation(validation)

    condition = filtered._where[0]
    sql, params = condition.to_sql("sqlite")

    assert sql == '"sample_id" IN (?, ?, ?, ?)'
    assert params == ["transcript_1", "transcript_2", "transcript_3", "transcript_4"]


def test_for_validation_duplicate_ids():
    """Test for_validation removes duplicate IDs."""
    validation = Validation(
        cases=[
            ValidationCase(id="transcript_1", target=True),
            ValidationCase(id="transcript_1", target=False),  # Duplicate
            ValidationCase(
                id=["transcript_2", "transcript_1"], target=True
            ),  # More duplicates
        ]
    )

    transcripts = MockTranscripts()
    filtered = transcripts.for_validation(validation)

    condition = filtered._where[0]
    sql, params = condition.to_sql("sqlite")

    # Should only have 2 unique IDs
    assert sql == '"sample_id" IN (?, ?)'
    assert params == ["transcript_1", "transcript_2"]


def test_for_validation_preserves_order():
    """Test for_validation preserves ID order when deduplicating."""
    validation = Validation(
        cases=[
            ValidationCase(id="id_c", target=True),
            ValidationCase(id="id_a", target=False),
            ValidationCase(id="id_b", target=True),
            ValidationCase(id="id_a", target=True),  # Duplicate
        ]
    )

    transcripts = MockTranscripts()
    filtered = transcripts.for_validation(validation)

    condition = filtered._where[0]
    sql, params = condition.to_sql("sqlite")

    # Order should be: id_c, id_a, id_b (first occurrence preserved)
    assert params == ["id_c", "id_a", "id_b"]


def test_for_validation_empty_cases():
    """Test for_validation with empty validation cases."""
    validation = Validation(cases=[])

    transcripts = MockTranscripts()
    filtered = transcripts.for_validation(validation)

    assert len(filtered._where) == 1

    condition = filtered._where[0]
    sql, params = condition.to_sql("sqlite")

    # Empty IN should return "1 = 0" (always false)
    assert sql == "1 = 0"
    assert params == []


def test_for_validation_large_id_list():
    """Test for_validation with >999 IDs (SQLite parameter limit)."""
    # Create 1500 validation cases to exceed SQLite's 999 parameter limit
    cases = [ValidationCase(id=f"id_{i}", target=i % 2 == 0) for i in range(1500)]
    validation = Validation(cases=cases)

    transcripts = MockTranscripts()
    filtered = transcripts.for_validation(validation)

    assert len(filtered._where) == 1

    condition = filtered._where[0]
    sql, params = condition.to_sql("sqlite")

    # Should have all 1500 IDs
    assert len(params) == 1500

    # SQL should use OR to combine multiple IN clauses
    assert "OR" in sql
    # Should have 2 chunks: 999 + 501
    assert sql.count("IN") == 2


def test_for_validation_combines_with_existing_conditions():
    """Test that for_validation combines with existing where conditions."""
    from inspect_scout._transcript.metadata import metadata as m

    validation = Validation(
        cases=[
            ValidationCase(id="transcript_1", target=True),
            ValidationCase(id="transcript_2", target=False),
        ]
    )

    transcripts = MockTranscripts()
    # Add an existing condition
    transcripts = transcripts.where(m.model == "gpt-4")
    # Add validation filter
    filtered = transcripts.for_validation(validation)

    # Should have 2 conditions now
    assert len(filtered._where) == 2

    # First condition is the model filter
    sql1, params1 = filtered._where[0].to_sql("sqlite")
    assert '"model" = ?' in sql1
    assert params1 == ["gpt-4"]

    # Second condition is the ID filter
    sql2, params2 = filtered._where[1].to_sql("sqlite")
    assert '"sample_id" IN (?, ?)' in sql2
    assert params2 == ["transcript_1", "transcript_2"]


def test_for_validation_sql_generation_sqlite():
    """Test SQL generation for SQLite dialect."""
    validation = Validation(
        cases=[
            ValidationCase(id="id1", target=True),
            ValidationCase(id="id2", target=False),
        ]
    )

    transcripts = MockTranscripts()
    filtered = transcripts.for_validation(validation)

    condition = filtered._where[0]
    sql, params = condition.to_sql("sqlite")

    assert sql == '"sample_id" IN (?, ?)'
    assert params == ["id1", "id2"]


def test_for_validation_sql_generation_postgres():
    """Test SQL generation for PostgreSQL dialect."""
    validation = Validation(
        cases=[
            ValidationCase(id="id1", target=True),
            ValidationCase(id="id2", target=False),
        ]
    )

    transcripts = MockTranscripts()
    filtered = transcripts.for_validation(validation)

    condition = filtered._where[0]
    sql, params = condition.to_sql("postgres")

    # PostgreSQL uses $1, $2 instead of ?
    assert sql == '"sample_id" IN ($1, $2)'
    assert params == ["id1", "id2"]


def test_for_validation_sql_generation_duckdb():
    """Test SQL generation for DuckDB dialect."""
    validation = Validation(
        cases=[
            ValidationCase(id="id1", target=True),
            ValidationCase(id="id2", target=False),
        ]
    )

    transcripts = MockTranscripts()
    filtered = transcripts.for_validation(validation)

    condition = filtered._where[0]
    sql, params = condition.to_sql("duckdb")

    assert sql == '"sample_id" IN (?, ?)'
    assert params == ["id1", "id2"]


def test_for_validation_does_not_modify_original():
    """Test that for_validation does not modify the original Transcripts object."""
    validation = Validation(
        cases=[
            ValidationCase(id="transcript_1", target=True),
        ]
    )

    transcripts = MockTranscripts()
    original_where_len = len(transcripts._where)

    # Create filtered version
    filtered = transcripts.for_validation(validation)

    # Original should be unchanged
    assert len(transcripts._where) == original_where_len
    # Filtered should have new condition
    assert len(filtered._where) == original_where_len + 1


def test_for_validation_with_predicate():
    """Test for_validation works with validation that has a predicate."""

    def custom_predicate(value, target):
        return value == target

    validation = Validation(
        cases=[
            ValidationCase(id="transcript_1", target=True),
        ],
        predicate=custom_predicate,
    )

    transcripts = MockTranscripts()
    filtered = transcripts.for_validation(validation)

    # Should still create the ID filter
    condition = filtered._where[0]
    sql, params = condition.to_sql("sqlite")

    assert sql == '"sample_id" IN (?)'
    assert params == ["transcript_1"]


def test_for_validation_chunk_boundary():
    """Test for_validation at exactly 999 IDs (boundary case)."""
    # Create exactly 999 validation cases
    cases = [ValidationCase(id=f"id_{i}", target=True) for i in range(999)]
    validation = Validation(cases=cases)

    transcripts = MockTranscripts()
    filtered = transcripts.for_validation(validation)

    condition = filtered._where[0]
    sql, params = condition.to_sql("sqlite")

    # Should NOT use OR (fits in single IN clause)
    assert "OR" not in sql
    assert len(params) == 999
    assert sql == '"sample_id" IN (' + ", ".join(["?"] * 999) + ")"


def test_for_validation_just_over_chunk_boundary():
    """Test for_validation with 1000 IDs (just over boundary)."""
    # Create 1000 validation cases (1 more than limit)
    cases = [ValidationCase(id=f"id_{i}", target=True) for i in range(1000)]
    validation = Validation(cases=cases)

    transcripts = MockTranscripts()
    filtered = transcripts.for_validation(validation)

    condition = filtered._where[0]
    sql, params = condition.to_sql("sqlite")

    # Should use OR to split into 2 chunks: 999 + 1
    assert "OR" in sql
    assert len(params) == 1000
    assert sql.count("IN") == 2
