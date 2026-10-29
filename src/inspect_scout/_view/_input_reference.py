"""Resolving reference-mode scan inputs for the viewer API."""

import contextvars
import functools
from logging import getLogger
from typing import Any, Awaitable, Callable, Mapping, NamedTuple

import anyio
from inspect_ai._util._async import _anyio_run_released
from inspect_ai.log import condense_events
from pydantic import BaseModel
from starlette.requests import Request

from .._transcript.reference import (
    InputReference,
    InputReferenceUnavailable,
    input_too_large,
    read_referenced_transcript,
)
from .._util._json import to_json_bytes_compact

logger = getLogger(__name__)

InputReferenceLocator = Callable[[Request, InputReference], Awaitable[str]]
"""Returns the location to read a reference from, or raises `InputReferenceUnavailable`.

Row values are untrusted when a server shows scans other users wrote, so a
multi-user host's locator must decide what the requesting user may read and
return a location it has checked, never the row's URI as given.

Only `.eval` locations can be read; any other is reported as `unavailable`.
Raise `InputReferenceUnavailable` for row-level refusals; it is shown to the
user with a 200. Any other exception propagates as a server error, deliberately,
so an outage does not read as a refusal.
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
    """A resolved row's `input` and `input_data`.

    Messages, events and ids match copy mode; top-level info carries identity
    fields only.
    """

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
            logger.exception(
                "Unable to resolve the input of transcript %s", ref.transcript_id
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
        # Condensed as copy mode records a transcript (`_serialize_input`).
        condensed_events, events_data = condense_events(transcript.events)
        condensed = transcript.model_copy(update={"events": condensed_events})
        # An attachment referenced many times is one string in memory but is
        # written out once per reference, so the output can dwarf the sample.
        if self._max_bytes is not None and _json_size_exceeds(
            (condensed, events_data), self._max_bytes
        ):
            raise input_too_large(self._max_bytes)
        return ResolvedInput(
            to_json_bytes_compact(condensed).decode("utf-8"),
            to_json_bytes_compact(events_data).decode("utf-8"),
        )


def _json_size_exceeds(value: Any, limit: int) -> bool:
    """Whether `value` serializes to more than about `limit` bytes of JSON.

    Sums string lengths without serializing (a shared string counts once per
    reference, as it is written), and stops as soon as the total passes
    `limit`.
    """
    total = 0
    stack: list[Any] = [value]
    while stack:
        item = stack.pop()
        if isinstance(item, str | bytes | bytearray):
            total += len(item) + 2
        elif isinstance(item, BaseModel):
            total += 2
            stack.extend(item.__dict__.values())
            if item.__pydantic_extra__:
                stack.extend(item.__pydantic_extra__.values())
        elif isinstance(item, Mapping):
            for key, child in item.items():
                total += len(str(key)) + 4
                stack.append(child)
        elif isinstance(item, list | tuple | set | frozenset):
            total += 2 + len(item)
            stack.extend(item)
        else:
            total += 8
        if total > limit:
            return True
    return False
