"""Resolves the per-location SQLite index file path in the local cache."""

import hashlib
from pathlib import Path

from .._util.appdirs import scout_cache_dir

# Bump to invalidate every existing on-disk scans index (e.g. when the
# ScanRow schema in store.py changes).
SCANS_INDEX_VERSION = 1


def scans_index_db_path(location: str) -> Path:
    """Return the SQLite index path for a scans location.

    Layout: ``<cache>/scans_index/v{VERSION}/<location_hash>/scans.sqlite``.
    The parent directory is created. The location is normalized (trailing
    slashes stripped) before hashing so equivalent paths share an index.
    """
    normalized = location.rstrip("/")
    location_hash = hashlib.sha256(normalized.encode()).hexdigest()[:16]
    db_dir = scout_cache_dir("scans_index") / f"v{SCANS_INDEX_VERSION}" / location_hash
    db_dir.mkdir(parents=True, exist_ok=True)
    return db_dir / "scans.sqlite"
