from pathlib import Path
from typing import Union

from upath import UPath


def normalize_for_hashing(path: Union[str, UPath]) -> str:
    """Normalizes a path for consistent hashing.

    In particular, deals with paths that have `file` protocols vs pure local
    file paths to ensure they are normalized to the same output form before
    hashing.
    """
    up = UPath(path)

    # Local filesystem variants
    if up.protocol in ("", "file"):
        if up.protocol == "file":
            # Just the file path omiting the protocol
            p = Path(up.path)
        else:
            # Since there is no protocol, take the path as is
            p = Path(str(up))

        return p.resolve().as_posix()

    # Remote/non-local paths
    return str(up)
