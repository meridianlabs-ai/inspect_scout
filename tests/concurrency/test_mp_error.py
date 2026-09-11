"""Fatal diagnostics survive pickling without provider objects or locals."""

import asyncio
import pickle
import sys
import threading
import traceback
from collections.abc import Iterator
from typing import Any

import pytest
from inspect_scout._concurrency._mp_error import WorkerProcessError, worker_error

if sys.version_info < (3, 11):
    from exceptiongroup import ExceptionGroup


class ProviderError(Exception):
    def __init__(self, message: str, *, response: object) -> None:
        super().__init__(message)
        self.response = response
        self.status_code = 529
        self.request_id = "request-fixture"


def _raise_provider_error() -> None:
    private_local = "private-local-value"
    response = {"body": "private-response-value", "lock": threading.Lock()}
    assert private_local
    raise ProviderError("provider unavailable", response=response)


def test_diagnostic_round_trip_detaches_provider_objects_and_locals() -> None:
    try:
        _raise_provider_error()
    except ProviderError as ex:
        payload = worker_error(3, ex)
    wire = pickle.dumps(payload)
    restored = pickle.loads(wire)
    assert restored == payload
    diagnostic = str(WorkerProcessError(restored))
    for detail in (
        "Worker 3",
        "ProviderError",
        "provider unavailable",
        "_raise_provider_error",
        "529",
        "request-fixture",
    ):
        assert detail in diagnostic
    assert b"private-response-value" not in wire
    assert b"private-local-value" not in wire


@pytest.mark.parametrize("grouped", [False, True])
def test_remote_chain_and_group_keep_text_without_borrowing_leaf_metadata(
    grouped: bool,
) -> None:
    try:
        try:
            _raise_provider_error()
        except ProviderError as ex:
            if grouped:
                raise ExceptionGroup(
                    "two failures", [ex, ValueError("other failure")]
                ) from None
            raise RuntimeError("outer failure") from ex
    except Exception as ex:
        payload = pickle.loads(pickle.dumps(worker_error(1, ex)))
    assert "provider unavailable" in payload.traceback
    assert "_raise_provider_error" in payload.traceback
    assert ("other failure" if grouped else "outer failure") in payload.traceback
    assert payload.status_code is None
    assert payload.request_id is None


class BrokenError(Exception):
    def __str__(self) -> str:
        raise ValueError("broken __str__")

    @property
    def status_code(self) -> int:
        raise ValueError("broken status")

    @property
    def request_id(self) -> str:
        raise ValueError("broken request")


def test_broken_message_and_metadata_do_not_replace_failure() -> None:
    try:
        raise BrokenError()
    except BrokenError as ex:
        payload = worker_error(1, ex)
    assert "BrokenError" in payload.type_name
    assert payload.message == "<exception message unavailable>"
    assert "test_broken_message_and_metadata" in payload.traceback
    assert payload.status_code is None
    assert payload.request_id is None
    pickle.dumps(payload)


@pytest.mark.parametrize("broken_frames", [False, True])
def test_formatter_fallback_retains_original_failure(
    monkeypatch: pytest.MonkeyPatch,
    broken_frames: bool,
) -> None:
    def broken_formatter(*args: Any, **kwargs: Any) -> list[str]:
        raise ValueError("formatter failed")

    monkeypatch.setattr(traceback.TracebackException, "format", broken_formatter)
    if broken_frames:
        monkeypatch.setattr(traceback, "format_tb", broken_formatter)
    try:
        raise RuntimeError("original failure")
    except RuntimeError as ex:
        payload = worker_error(1, ex)
    assert "original failure" in payload.traceback
    assert "builtins.RuntimeError" in payload.traceback
    if not broken_frames:
        assert "test_formatter_fallback" in payload.traceback


class UnpicklableString(str):
    def __reduce__(self) -> str:
        raise TypeError("must not send a scalar subclass")


@pytest.mark.parametrize(
    "status,request_id", [(True, []), ("529", UnpicklableString("id"))]
)
def test_metadata_requires_plain_scalars(status: object, request_id: object) -> None:
    class MetadataError(Exception):
        status_code: object
        request_id: object

    error = MetadataError("failure")
    error.status_code, error.request_id = status, request_id
    payload = worker_error(1, error)
    assert payload.status_code is None
    assert payload.request_id is None
    pickle.dumps(payload)


def test_exception_message_is_detached_from_a_string_subclass() -> None:
    class SubclassMessageError(Exception):
        def __str__(self) -> str:
            return UnpicklableString("subclass message")

    payload = worker_error(1, SubclassMessageError())
    assert pickle.loads(pickle.dumps(payload)).message == "subclass message"


def test_bad_exception_notes_keep_worker_frames() -> None:
    class BrokenNotes(list[str]):
        def __iter__(self) -> Iterator[str]:
            raise ValueError("broken notes iteration")

    class NotesError(Exception):
        __notes__ = BrokenNotes(["fixture note"])

    try:
        raise NotesError("original failure")
    except NotesError as ex:
        payload = pickle.loads(pickle.dumps(worker_error(1, ex)))
    assert ", in test_bad_exception_notes_keep_worker_frames\n" in payload.traceback
    assert "original failure" in payload.traceback
    assert "Formatting stacktrace failed" not in payload.traceback


def test_formatting_does_not_swallow_cancellation() -> None:
    class InterruptedError(Exception):
        def __str__(self) -> str:
            raise asyncio.CancelledError()

    with pytest.raises(asyncio.CancelledError):
        worker_error(1, InterruptedError())


@pytest.mark.parametrize("broken_attribute", ["__module__", "__qualname__"])
def test_broken_type_metadata_does_not_replace_failure(broken_attribute: str) -> None:
    class BrokenType(type):
        def __getattribute__(cls, name: str) -> Any:
            if name == broken_attribute:
                raise ValueError("broken type metadata")
            return super().__getattribute__(name)

    class LocalError(Exception, metaclass=BrokenType):
        pass

    error = LocalError("original worker failure")
    try:
        raise error
    except LocalError:
        pass
    payload = pickle.loads(pickle.dumps(worker_error(1, error)))
    assert payload.message == "original worker failure"
    assert "test_broken_type_metadata" in payload.traceback
    assert "original worker failure" in str(WorkerProcessError(payload))


def test_type_module_is_not_formatted_as_an_arbitrary_object() -> None:
    class BrokenModule:
        def __str__(self) -> str:
            raise ValueError("broken module formatting")

    class LocalError(Exception):
        pass

    type.__setattr__(LocalError, "__module__", BrokenModule())
    payload = pickle.loads(pickle.dumps(worker_error(1, LocalError("original"))))
    assert "LocalError" in payload.type_name
    assert payload.message == "original"


@pytest.mark.parametrize("attribute", ["__module__", "__qualname__"])
def test_type_metadata_subclass_keeps_available_frames(attribute: str) -> None:
    class BrokenString(str):
        def __str__(self) -> str:
            raise ValueError("broken metadata string")

        def __eq__(self, other: object) -> bool:
            raise ValueError("broken metadata comparison")

        def __hash__(self) -> int:
            return str.__hash__(self)

        def __reduce__(self) -> str:
            raise TypeError("must not send metadata object")

    class LocalError(Exception):
        pass

    type.__setattr__(LocalError, attribute, BrokenString("fixture_type"))
    error = LocalError("original worker failure")
    try:
        raise error
    except LocalError:
        pass
    payload = pickle.loads(pickle.dumps(worker_error(1, error)))
    assert "fixture_type" in payload.type_name
    assert "test_type_metadata_subclass" in payload.traceback
    assert "original worker failure" in payload.traceback
