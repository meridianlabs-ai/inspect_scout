"""Tests for sqlite cache in eval_log.py."""

import sqlite3
from pathlib import Path

import pytest
from inspect_scout._transcript.eval_log import (
    _compute_cache_key_from_logs,
    _sqlite_cache,
)


def test_compute_cache_key_from_single_path() -> None:
    """Cache key should be computed from single path."""
    key = _compute_cache_key_from_logs("/some/path/to/logs")
    assert isinstance(key, str)
    assert len(key) == 64  # SHA256 hex digest length


def test_compute_cache_key_from_multiple_paths() -> None:
    """Cache key should be order-independent for multiple paths."""
    key1 = _compute_cache_key_from_logs(["/path1", "/path2"])
    key2 = _compute_cache_key_from_logs(["/path2", "/path1"])
    assert key1 == key2  # Order independent due to sorting


def test_compute_cache_key_uniqueness() -> None:
    """Different paths should produce different cache keys."""
    key1 = _compute_cache_key_from_logs("/path1")
    key2 = _compute_cache_key_from_logs("/path2")
    assert key1 != key2


def test_sqlite_cache_named_memory_db() -> None:
    """Named in-memory sqlite databases with cache=shared should share data."""
    cache_key = "test_cache_key_sqlite"

    # Create first connection and add data
    conn1 = sqlite3.connect(f"file:{cache_key}?mode=memory&cache=shared", uri=True)
    conn1.execute("CREATE TABLE test (id INTEGER)")
    conn1.execute("INSERT INTO test VALUES (42)")
    conn1.commit()

    # Keep sentinel connection (simulates what _sqlite_cache does)
    _sqlite_cache[cache_key] = conn1

    # Second connection should see the data
    conn2 = sqlite3.connect(f"file:{cache_key}?mode=memory&cache=shared", uri=True)
    result = conn2.execute("SELECT * FROM test").fetchall()
    assert result == [(42,)]

    # Clean up
    conn2.close()
    _sqlite_cache.pop(cache_key, None)
    conn1.close()


def test_sqlite_cache_persists_with_sentinel() -> None:
    """Data should persist as long as sentinel connection is open."""
    cache_key = "test_sentinel_persistence"

    # Create and populate db
    conn1 = sqlite3.connect(f"file:{cache_key}?mode=memory&cache=shared", uri=True)
    conn1.execute("CREATE TABLE test (val TEXT)")
    conn1.execute("INSERT INTO test VALUES ('hello')")
    conn1.commit()

    # Keep sentinel
    _sqlite_cache[cache_key] = conn1

    # Open, use, and close another connection
    conn2 = sqlite3.connect(f"file:{cache_key}?mode=memory&cache=shared", uri=True)
    conn2.execute("SELECT * FROM test").fetchall()
    conn2.close()

    # Data should still be accessible via new connection
    conn3 = sqlite3.connect(f"file:{cache_key}?mode=memory&cache=shared", uri=True)
    result = conn3.execute("SELECT * FROM test").fetchall()
    assert result == [("hello",)]

    # Clean up
    conn3.close()
    _sqlite_cache.pop(cache_key, None)
    conn1.close()


@pytest.mark.skipif(
    not Path("tests/test_helpers/log_samples/example_log.json").exists(),
    reason="Test log file not available",
)
def test_eval_log_view_caches_connection() -> None:
    """EvalLogTranscriptsView should reuse cached sqlite connection."""
    import asyncio

    from inspect_scout._transcript.eval_log import EvalLogTranscriptsView

    log_path = "tests/test_helpers/log_samples/example_log.json"

    async def run_test() -> None:
        # First view - should create and cache the db
        view1 = EvalLogTranscriptsView(log_path)
        await view1.connect()

        cache_key = view1._cache_key
        assert cache_key is not None
        assert cache_key in _sqlite_cache

        await view1.disconnect()

        # Second view - should reuse cached db
        view2 = EvalLogTranscriptsView(log_path)
        await view2.connect()

        assert view2._cache_key == cache_key
        # Connection should work (db still exists due to sentinel)
        assert view2._conn is not None

        await view2.disconnect()

        # Clean up
        if cache_key in _sqlite_cache:
            _sqlite_cache[cache_key].close()
            _sqlite_cache.pop(cache_key, None)

    asyncio.run(run_test())
