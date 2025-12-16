from typing import Any

from fastapi.responses import JSONResponse
from inspect_ai._util.json import to_json_safe
from typing_extensions import override
from upath import UPath


class InspectPydanticJSONResponse(JSONResponse):
    """Like the standard starlette JSON, but allows NaN."""

    @override
    def render(self, content: Any) -> bytes:
        return to_json_safe(content)


async def default_transcripts_dir() -> str:
    """Return resolved path to transcripts dir, scrounging scan results for a plausible default."""
    return (
        UPath(await _scrounged_transcripts_dir() or "file://./transcripts")
        .resolve()
        .as_posix()
    )


async def _scrounged_transcripts_dir() -> str | None:
    # TODO: Scrounge any scan results to find a plausible transcript dir
    return None
