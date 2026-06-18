import hashlib
from pathlib import Path

import pytest
from inspect_scout._scanjobs.cache_path import (
    SCANS_INDEX_VERSION,
    scans_index_db_path,
)


def test_path_is_deterministic_and_versioned(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        "inspect_scout._scanjobs.cache_path.scout_cache_dir",
        lambda subdir=None: tmp_path / subdir if subdir else tmp_path,
    )
    p1 = scans_index_db_path("/scans/dir")
    p2 = scans_index_db_path("/scans/dir/")  # trailing slash normalized

    assert p1 == p2
    assert p1.name == "scans.sqlite"
    assert p1.parent.parent.name == f"v{SCANS_INDEX_VERSION}"
    assert p1.parent.parent.parent.name == "scans_index"
    assert p1.parent.is_dir()  # parent created


def test_distinct_locations_get_distinct_dirs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        "inspect_scout._scanjobs.cache_path.scout_cache_dir",
        lambda subdir=None: tmp_path / subdir if subdir else tmp_path,
    )
    a = scans_index_db_path("s3://bucket/scans-a")
    b = scans_index_db_path("s3://bucket/scans-b")

    assert a.parent != b.parent
    expected_hash = hashlib.sha256(b"s3://bucket/scans-a").hexdigest()[:16]
    assert a.parent.name == expected_hash
