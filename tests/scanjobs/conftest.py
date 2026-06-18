# tests/scanjobs/conftest.py
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _isolated_scans_cache(
    tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Redirect the scout cache dir so scan-index tests never touch the real cache."""
    cache_root = tmp_path_factory.mktemp("scout_cache")

    def fake_cache_dir(subdir: str | None = None) -> Path:
        path = cache_root / subdir if subdir else cache_root
        path.mkdir(parents=True, exist_ok=True)
        return path

    monkeypatch.setattr(
        "inspect_scout._scanjobs.cache_path.scout_cache_dir", fake_cache_dir
    )
