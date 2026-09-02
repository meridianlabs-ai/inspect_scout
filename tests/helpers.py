"""Shared test utilities."""

import secrets
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, ContextManager, Iterator
from unittest.mock import patch

from inspect_ai._util.kvstore import inspect_kvstore
from inspect_scout._recorder.active_scans_store import (
    ActiveScansStore,
    active_scans_store,
)


@contextmanager
def temp_kvstore() -> Iterator[str]:
    """Context manager that creates a temp kvstore and cleans up the file on exit.

    Yields:
        The kvstore name to pass to samples_df_with_caching.
    """
    name = f"__testing_{secrets.token_hex(4)}__"
    try:
        yield name
    finally:
        # filename is computed at construction; no need to open the store
        # (which would create the file) just to delete it
        Path(inspect_kvstore(name).filename).unlink(missing_ok=True)


@contextmanager
def temp_active_scans_store() -> Iterator[str]:
    """Redirect the active-scans store to a temp kvstore, cleaned up on exit.

    Keeps scan-running tests out of the developer's live scout_active_scans
    store. Yields the temporary kvstore name.
    """
    with temp_kvstore() as name:
        with patch("inspect_scout._recorder.active_scans_store._STORE_NAME", name):
            yield name


def active_scans_store_spy(
    method_name: str, on_call: Callable[..., None]
) -> Callable[[], ContextManager[ActiveScansStore]]:
    """Store factory whose store calls on_call(store, *args) after method_name.

    Install with monkeypatch.setattr(scan_module, "active_scans_store", ...),
    patching the name where _scan.py looks it up rather than where it lives.
    """

    @contextmanager
    def spying_store() -> Iterator[ActiveScansStore]:
        with active_scans_store() as store:
            real = getattr(store, method_name)

            def spied(*args: Any, **kwargs: Any) -> Any:
                result = real(*args, **kwargs)
                on_call(store, *args, **kwargs)
                return result

            setattr(store, method_name, spied)
            yield store

    return spying_store
