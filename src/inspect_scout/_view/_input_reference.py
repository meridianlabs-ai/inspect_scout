"""Resolving reference-mode scan inputs for the viewer API."""

import contextvars
import functools
from logging import getLogger
from typing import Any, Awaitable, Callable, Mapping, NamedTuple

import anyio
from inspect_ai._util._async import _anyio_run_released
from starlette.requests import Request

from .._scanner.result import _serialize_input
from .._transcript.reference import (
    InputReference,
    InputReferenceUnavailable,
    read_referenced_transcript,
)

logger = getLogger(__name__)

InputReferenceLocator = Callable[[Request, InputReference], Awaitable[str]]
"""Returns the location to read a reference from, or raises `InputReferenceUnavailable`.

Row values are untrusted when a server shows scans other users wrote, so a
multi-user host's locator must decide what the requesting user may read and
return a location it has checked, never the row's URI as given.
"""


async def source_uri_locator(request: Request, ref: InputReference) -> str:
    """Locate a reference at the row's own `transcript_source_uri`.

    For single-user servers such as `scout view` only: the row's URI is read
    with the server's credentials.
    """
    if not ref.transcript_source_uri:
        raise InputReferenceUnavailable(
            "not_found", "The result row does not name its source transcript."
        )
    return ref.transcript_source_uri


class ResolvedInput(NamedTuple):
    """A resolved row's `input` and `input_data`, as copy mode stores them."""

    input: str
    input_data: str | None


class InputReferenceResolver:
    """Rebuilds the input of reference-mode result rows for the viewer.

    Reads run in worker threads, each on a private event loop with a fresh
    context, at most `concurrency` at a time, so a large parse neither blocks
    the server's loop nor touches objects bound to it (it may be uvloop).
    """

    def __init__(
        self,
        locator: InputReferenceLocator,
        *,
        max_bytes: int | None = None,
        concurrency: int = 2,
    ) -> None:
        self._locator = locator
        self._max_bytes = max_bytes
        self._limiter = anyio.CapacityLimiter(concurrency)

    async def resolve(self, request: Request, row: Mapping[str, Any]) -> ResolvedInput:
        """Resolve a reference row's input.

        Raises:
            InputReferenceUnavailable: The input can't be shown.
        """
        ref = InputReference.from_row(row)
        location = await self._locator(request, ref)
        try:
            return await anyio.to_thread.run_sync(
                self._read, location, ref, limiter=self._limiter
            )
        except InputReferenceUnavailable:
            raise
        except Exception as ex:
            logger.warning(
                "Unable to resolve the input of transcript %s",
                ref.transcript_id,
                exc_info=True,
            )
            raise InputReferenceUnavailable(
                "unavailable", "The referenced input could not be read."
            ) from ex

    def _read(self, location: str, ref: InputReference) -> ResolvedInput:
        # A fresh context: the request's copied context can hold the host's
        # shared AsyncFilesystem, whose S3 client is bound to the server loop.
        # `_anyio_run_released` drops anyio's per-loop state after the run,
        # which would otherwise keep the loop and its result alive forever.
        return contextvars.Context().run(
            _anyio_run_released, functools.partial(self._read_async, location, ref)
        )

    async def _read_async(self, location: str, ref: InputReference) -> ResolvedInput:
        transcript = await read_referenced_transcript(
            location, ref, max_bytes=self._max_bytes
        )
        input_bytes, data_bytes = _serialize_input(
            transcript, "transcript", pool_dedup=True
        )
        return ResolvedInput(
            input_bytes.decode("utf-8"),
            data_bytes.decode("utf-8") if data_bytes is not None else None,
        )
