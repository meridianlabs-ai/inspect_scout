"""Normalize fatal worker exceptions before multiprocessing serialization."""

import traceback

from ._mp_common import WorkerError


def worker_error(worker_id: int, exception: Exception) -> WorkerError:
    """Capture text and root-exception metadata without retaining live objects."""
    type_name = f"{type(exception).__module__}.{type(exception).__qualname__}"
    try:
        message = str.__str__(str(exception))
    except Exception:
        message = "<exception message unavailable>"

    try:
        remote_traceback = "".join(
            traceback.format_exception(
                type(exception), exception, exception.__traceback__
            )
        )
    except Exception:
        # A broken exception formatter must not discard the original stack.
        try:
            frames = "".join(traceback.format_tb(exception.__traceback__))
        except Exception:
            frames = "<traceback frames unavailable>\n"
        remote_traceback = f"{frames}{type_name}: {message}\n"

    # Do not choose an arbitrary cause/group leaf's metadata, or transport
    # subclasses with their own reducers and attached object graphs.
    status = _optional_attribute(exception, "status_code")
    request = _optional_attribute(exception, "request_id")
    return WorkerError(
        worker_id=worker_id,
        type_name=type_name,
        message=message,
        traceback=remote_traceback,
        status_code=status if type(status) is int else None,
        request_id=request if type(request) is str else None,
    )


def _optional_attribute(exception: Exception, name: str) -> object:
    try:
        return getattr(exception, name, None)
    except Exception:
        return None


class WorkerProcessError(RuntimeError):
    """Parent-side diagnostic; the provider exception is never reconstructed."""

    def __init__(self, error: WorkerError) -> None:
        details = [f"Worker {error.worker_id}: {error.type_name}: {error.message}"]
        if error.status_code is not None:
            details.append(f"HTTP status: {error.status_code}")
        if error.request_id is not None:
            details.append(f"Request ID: {error.request_id}")
        details.append(f"Remote traceback:\n{error.traceback}")
        super().__init__("\n".join(details))
