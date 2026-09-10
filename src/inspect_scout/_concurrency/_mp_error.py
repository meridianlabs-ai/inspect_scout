"""Normalize fatal worker exceptions before multiprocessing serialization."""

import traceback

from ._mp_common import WorkerError


def worker_error(worker_id: int, exception: Exception) -> WorkerError:
    """Capture text and root-exception metadata without retaining live objects."""
    # Class metadata can be malformed or supplied by a custom metaclass.
    type_metadata_available = True
    try:
        name = type(exception).__qualname__
        type_metadata_available = type(name) is str
        type_name = str.__str__(name)
    except Exception:
        type_name = "<exception type unavailable>"
        type_metadata_available = False
    try:
        module = type(exception).__module__
        type_metadata_available = type_metadata_available and type(module) is str
        module = str.__str__(module)
    except Exception:
        type_metadata_available = False
    else:
        type_name = f"{module}.{type_name}"
    try:
        message = str.__str__(str(exception))
    except Exception:
        message = "<exception message unavailable>"

    remote_traceback = None
    if type_metadata_available:
        try:
            # Instrumentation can make format_exception return an error message
            # instead of raising, preventing our worker-frame fallback.
            remote_traceback = "".join(
                traceback.TracebackException(
                    type(exception), exception, exception.__traceback__, compact=True
                ).format()
            )
        except Exception:
            pass
    if remote_traceback is None:
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
