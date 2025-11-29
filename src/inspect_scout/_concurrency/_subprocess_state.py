"""Subprocess state for multiprocessing - tracks state to transfer to spawned processes."""

_plugin_directories: set[str] = set()
_log_level: str | None = None


def register_plugin_directory(directory: str) -> None:
    """Register a plugin directory to be added to sys.path in subprocesses."""
    _plugin_directories.add(directory)


def get_plugin_directories() -> set[str]:
    """Get all registered plugin directories."""
    return _plugin_directories.copy()


def set_log_level(level: str | None) -> None:
    """Set log level to be used in subprocesses."""
    global _log_level
    _log_level = level


def get_log_level() -> str | None:
    """Get log level for subprocesses."""
    return _log_level
