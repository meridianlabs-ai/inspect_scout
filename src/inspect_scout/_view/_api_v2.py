"""V2 API orchestrator - creates FastAPI app and includes all routers."""

from pathlib import Path as PathlibPath

from fastapi import FastAPI

from ._api_v2_config import create_config_router
from ._api_v2_dist import create_dist_router
from ._api_v2_scanners import create_scanners_router
from ._api_v2_scans import create_scans_router
from ._api_v2_search import create_search_router
from ._api_v2_topics import create_topics_router
from ._api_v2_transcripts import create_transcripts_router
from ._api_v2_validations import create_validation_router
from .types import ViewConfig

API_VERSION = "2.0.0-alpha"


def v2_api_app(
    view_config: ViewConfig | None = None,
    streaming_batch_size: int = 1024,
    dist_path: PathlibPath | None = None,
) -> FastAPI:
    """Create V2 API FastAPI app.

    WARNING: This is an ALPHA API. Expect breaking changes without notice.
    Do not depend on this API for production use.
    """
    view_config = view_config or ViewConfig()

    app = FastAPI(
        title="Inspect Scout Viewer API",
        version=API_VERSION,
    )
    app.include_router(create_config_router(view_config=view_config))
    app.include_router(create_dist_router(dist_path=dist_path))
    app.include_router(create_topics_router())
    app.include_router(create_transcripts_router())
    app.include_router(create_scans_router(streaming_batch_size=streaming_batch_size))
    app.include_router(create_scanners_router())
    app.include_router(create_validation_router(PathlibPath.cwd()))
    app.include_router(create_search_router())

    return app
