"""Dist REST API endpoint."""

from pathlib import Path

from fastapi import APIRouter, HTTPException
from starlette.status import HTTP_404_NOT_FOUND

from ._api_v2_types import DistResponse
from ._server_common import InspectPydanticJSONResponse


def create_dist_router(dist_path: Path | None = None) -> APIRouter:
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
        if dist_path is None:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail=(
                    "Unable to resolve dist directory path. This should not happen once the server has started."
                ),
            ) from None

        return DistResponse(path=dist_path.as_posix())

    return router
