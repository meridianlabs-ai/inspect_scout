"""Plugin context for multiprocessing - tracks directories for sys.path setup."""

# Module-level set to track all plugin directories (scanjobs, scanners, etc.)
# These directories need to be added to sys.path in spawned subprocesses
# for user imports to work (e.g., "from scanners.foo import bar")
_plugin_directories: set[str] = set()


def register_plugin_directory(directory: str) -> None:
    """Register a plugin directory to be added to sys.path in subprocesses."""
    _plugin_directories.add(directory)


def get_plugin_directories() -> set[str]:
    """Get all registered plugin directories."""
    return _plugin_directories.copy()
