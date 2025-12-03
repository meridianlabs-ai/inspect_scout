"""Shared test utilities."""

import secrets
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

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
        with inspect_kvstore(name) as kvstore:
            path = kvstore.filename
        Path(path).unlink()
