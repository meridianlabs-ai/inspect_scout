"""V2 API orchestrator - creates FastAPI app and includes all routers."""

from pathlib import Path as PathlibPath

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .._query import UnknownColumnError
from ._api_v2_config import create_config_router
from ._api_v2_dist import create_dist_router
from ._api_v2_scanners import create_scanners_router
from ._api_v2_scans import create_scans_router
from ._api_v2_search import create_search_router
from ._api_v2_topics import create_topics_router
from ._api_v2_transcripts import create_transcripts_router
from ._api_v2_validations import create_validation_router
from ._input_reference import InputReferenceLocator, InputReferenceResolver
from .types import ViewConfig

API_VERSION = "2.0.0-alpha"


def v2_api_app(
    view_config: ViewConfig | None = None,
    streaming_batch_size: int = 1024,
    dist_path: PathlibPath | None = None,
    input_reference_locator: InputReferenceLocator | None = None,
    input_reference_max_bytes: int | None = None,
    input_reference_concurrency: int = 2,
) -> FastAPI:
    """Create V2 API FastAPI app.

    WARNING: This is an ALPHA API. Expect breaking changes without notice.
    Do not depend on this API for production use.

    Args:
        view_config: Viewer configuration.
        streaming_batch_size: Batch size for Arrow IPC streaming.
        dist_path: Directory of the built viewer.
        input_reference_locator: Locates the transcript of a reference-mode
            result row so its input can be shown. Without one, such rows are
            not resolved. A server showing other users' scans must authorize
            and map the location itself (see `InputReferenceLocator`).
        input_reference_max_bytes: Largest uncompressed sample to resolve.
        input_reference_concurrency: Most references resolved at once.
    """
    view_config = view_config or ViewConfig()
    input_reference_resolver = (
        InputReferenceResolver(
            input_reference_locator,
            max_bytes=input_reference_max_bytes,
            concurrency=input_reference_concurrency,
        )
        if input_reference_locator is not None
        else None
    )

    app = FastAPI(
        title="Inspect Scout Viewer API",
        version=API_VERSION,
    )

    @app.exception_handler(UnknownColumnError)
    async def unknown_column_handler(
        _request: Request, exc: UnknownColumnError
    ) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    app.include_router(create_config_router(view_config=view_config))
    app.include_router(create_dist_router(dist_path=dist_path))
    app.include_router(create_topics_router())
    app.include_router(create_transcripts_router())
    app.include_router(
        create_scans_router(
            streaming_batch_size=streaming_batch_size,
            input_reference_resolver=input_reference_resolver,
        )
    )
    app.include_router(create_scanners_router())
    app.include_router(create_validation_router(PathlibPath.cwd()))
    app.include_router(create_search_router())

    return app
