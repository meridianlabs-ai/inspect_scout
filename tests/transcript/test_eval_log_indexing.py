"""Tests for concurrent multi-log indexing in eval_log.py."""

import shutil
from pathlib import Path

import pandas as pd
import pytest
from inspect_ai.analysis import samples_df
from inspect_scout._transcript.eval_log import (
    TranscriptColumns,
    _read_samples_per_log,
    _split_df_by_log,
)

LOGS_DIR = Path(__file__).parent.parent / "recorder" / "logs"
LOG_1 = LOGS_DIR / "2025-09-23T08-09-58-04-00_popularity_DN2wbX2ZvACsBpjwptzBRo.eval"
LOG_2 = (
    LOGS_DIR / "2025-09-23T08-09-58-04-00_security-guide_LuxZJVwvymC3S3SyoJczxB.eval"
)


def test_read_samples_per_log_matches_individual_reads() -> None:
    """A multi-path read yields the same per-log frames as individual reads."""
    paths = [LOG_1.as_posix(), LOG_2.as_posix()]

    batched = _read_samples_per_log(paths)
    individual = [_read_samples_per_log([path])[0] for path in paths]

    assert len(batched) == len(paths)
    for batched_df, individual_df in zip(batched, individual, strict=True):
        # a batched frame may carry extra all-null columns contributed by
        # other logs in the batch (e.g. score_* columns of another task);
        # for the log's own columns the content must match
        extra = [c for c in batched_df.columns if c not in individual_df.columns]
        assert all(batched_df[c].isna().all() for c in extra)
        pd.testing.assert_frame_equal(
            batched_df[list(individual_df.columns)],
            individual_df,
            check_dtype=False,
        )


def test_read_samples_per_log_sets_transcript_id() -> None:
    """Each per-log frame carries transcript_id derived from sample_id."""
    dfs = _read_samples_per_log([LOG_1.as_posix(), LOG_2.as_posix()])
    for df in dfs:
        assert not df.empty
        assert df["transcript_id"].tolist() == df["sample_id"].tolist()


def test_read_samples_per_log_duplicate_logs(tmp_path: Path) -> None:
    """Copies of the same eval log each yield their full set of samples.

    inspect_ai de-duplicates evals within a multi-path call, so without the
    re-read safeguard the duplicate file would come back empty (and poison
    the per-file cache with an empty entry).
    """
    copy_1 = tmp_path / "copy_1.eval"
    copy_2 = tmp_path / "copy_2.eval"
    shutil.copy(LOG_1, copy_1)
    shutil.copy(LOG_1, copy_2)

    reference = samples_df([LOG_1.as_posix()], TranscriptColumns)
    dfs = _read_samples_per_log([copy_1.as_posix(), copy_2.as_posix()])

    assert len(dfs) == 2
    for df in dfs:
        assert len(df) == len(reference)
        assert sorted(df["sample_id"].tolist()) == sorted(
            reference["sample_id"].tolist()
        )


def test_split_df_by_log_partitions_rows() -> None:
    """Rows are partitioned by their log value, in the order of paths."""
    df = pd.DataFrame(
        {
            "log": ["/logs/log_b", "/logs/log_a", "/logs/log_b", "/logs/log_a"],
            "sample_id": ["s1", "s2", "s3", "s4"],
        }
    )

    dfs = _split_df_by_log(df, ["/logs/log_a", "/logs/log_b", "/logs/log_c"])

    assert dfs[0]["sample_id"].tolist() == ["s2", "s4"]
    assert dfs[1]["sample_id"].tolist() == ["s1", "s3"]
    assert dfs[2].empty
    assert list(dfs[2].columns) == ["log", "sample_id"]


def test_split_df_by_log_matches_native_paths() -> None:
    """Requested file:// paths match log values in native (stripped) form."""
    df = pd.DataFrame({"log": ["/logs/log_a"], "sample_id": ["s1"]})
    dfs = _split_df_by_log(df, ["file:///logs/log_a"])
    assert dfs[0]["sample_id"].tolist() == ["s1"]


def test_split_df_by_log_empty_df() -> None:
    """An empty DataFrame splits into empty frames, one per path."""
    dfs = _split_df_by_log(pd.DataFrame(), ["/logs/log_a", "/logs/log_b"])
    assert len(dfs) == 2
    assert all(df.empty for df in dfs)


def test_split_df_by_log_unrequested_log_raises() -> None:
    """Rows for a log that was not requested raise instead of being dropped."""
    df = pd.DataFrame(
        {"log": ["/logs/log_a", "/logs/log_x"], "sample_id": ["s1", "s2"]}
    )
    with pytest.raises(RuntimeError, match="log_x"):
        _split_df_by_log(df, ["/logs/log_a"])
