"""Subprocess state for multiprocessing - tracks state to transfer to spawned processes."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ._mp_common import ModelContext

_plugin_directories: set[str] = set()
_log_level: str | None = None
_model_context: ModelContext | None = None


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


def set_model_context(ctx: ModelContext) -> None:
    """Set model context to be used in subprocesses."""
    global _model_context
    _model_context = ctx


def get_model_context() -> ModelContext:
    """Get model context for subprocesses."""
    assert _model_context is not None, "model_context not set"
    return _model_context
