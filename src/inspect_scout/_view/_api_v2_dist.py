"""Dist REST API endpoint."""

import anyio
from fastapi import APIRouter, HTTPException
from inspect_ai._lfs import LFSError, resolve_lfs_directory
from starlette.status import HTTP_503_SERVICE_UNAVAILABLE

from inspect_scout._util.appdirs import scout_cache_dir

from ._api_v2_types import DistResponse
from ._dist_constants import DIST_DIR, REPO_URL
from ._server_common import InspectPydanticJSONResponse


def create_dist_router() -> APIRouter:
    """Create dist API router.

    Returns:
        Configured APIRouter with dist directory endpoint.
    """
    router = APIRouter(tags=["dist"])

    @router.get(
        "/dist",
        response_model=DistResponse,
        response_class=InspectPydanticJSONResponse,
        summary="Resolve dist directory",
        description="Returns the absolute path to the frontend dist directory, "
        "downloading from Git LFS if needed.",
    )
    async def dist() -> DistResponse:
        """Resolve the frontend dist directory path."""
        try:
            resolved = await anyio.to_thread.run_sync(
                lambda: resolve_lfs_directory(
                    DIST_DIR,
                    cache_dir=scout_cache_dir("dist"),
                    repo_url=REPO_URL,
                )
            )
        except LFSError as e:
            raise HTTPException(
                status_code=HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    f"Failed to resolve dist directory: {e}\n"
                    "To fix this, either:\n"
                    "  1. Install Git LFS: brew install git-lfs && git lfs install && git lfs pull\n"
                    "  2. Build locally: cd src/inspect_scout/_view/ts-mono && pnpm build"
                ),
            ) from None

        return DistResponse(path=resolved.as_posix())

    return router
