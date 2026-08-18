"""Shared test utilities."""

import secrets
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator
from unittest.mock import patch

from inspect_ai._util.kvstore import inspect_kvstore


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

    Keeps tests that run real scans from writing into the developer's live
    scout_active_scans store (and from sweeping its real entries).

    Yields:
        The temporary kvstore name.
    """
    with temp_kvstore() as name:
        with patch("inspect_scout._recorder.active_scans_store._STORE_NAME", name):
            yield name
