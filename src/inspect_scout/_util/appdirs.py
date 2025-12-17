from pathlib import Path

from inspect_ai._util.appdirs import package_data_dir
from platformdirs import user_cache_path

from inspect_scout._util.constants import PKG_NAME


def scout_data_dir(subdir: str) -> Path:
    """Get platform-appropriate data directory for inspect_scout."""
    return package_data_dir(PKG_NAME, subdir)


def scout_cache_dir(subdir: str | None = None) -> Path:
    """Get platform-appropriate cache directory for inspect_scout.

    Args:
        subdir: Optional subdirectory within the cache.

    Returns:
        Path to cache directory (created if it doesn't exist).
    """
    cache_dir = user_cache_path(PKG_NAME)
    if subdir:
        cache_dir = cache_dir / subdir
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir
