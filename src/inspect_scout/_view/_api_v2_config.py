"""Config REST API endpoints."""

from pathlib import Path as PathlibPath

from fastapi import APIRouter, Header, HTTPException, Request, Response
from inspect_ai._util.error import PrerequisiteError
from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_412_PRECONDITION_FAILED,
)
from upath import UPath

from .._project._project import (
    EtagMismatchError,
    read_project,
    read_project_config_with_etag,
    write_project_config,
)
from .._project.types import ProjectConfig
from .._util.constants import DEFAULT_SCANS_DIR
from ._api_v2_types import AppConfig, AppDir
from ._server_common import InspectPydanticJSONResponse
from .invalidationTopics import notify_topics
from .types import ViewConfig


def create_config_router(
    view_config: ViewConfig | None = None,
) -> APIRouter:
    """Create config API router.

    Args:
        view_config: View configuration.

    Returns:
        Configured APIRouter with config endpoints.
    """
    router = APIRouter(tags=["config"])
    view_config = view_config or ViewConfig()

    @router.get(
        "/app-config",
        response_model=AppConfig,
        response_class=InspectPydanticJSONResponse,
        summary="Get application configuration",
        description="Returns app config including transcripts and scans directories.",
    )
    async def config(request: Request) -> AppConfig:
        """Return application configuration."""
        project = read_project()
        transcripts_path = view_config.transcripts_cli or project.transcripts
        scans_path = view_config.scans_cli or project.scans or DEFAULT_SCANS_DIR
        return AppConfig(
            **project.model_dump(exclude={"transcripts", "scans", "results"}),
            home_dir=UPath(PathlibPath.home()).resolve().as_uri(),
            project_dir=UPath(PathlibPath.cwd()).resolve().as_uri(),
            transcripts=AppDir(
                dir=UPath(transcripts_path).resolve().as_uri(),
                source="cli" if view_config.transcripts_cli else "project",
            )
            if transcripts_path is not None
            else None,
            scans=AppDir(
                dir=UPath(scans_path).resolve().as_uri(),
                source="cli" if view_config.scans_cli else "project",
            ),
        )

    @router.get(
        "/project/config",
        response_model=ProjectConfig,
        response_class=InspectPydanticJSONResponse,
        summary="Get project configuration",
        description="Returns the project configuration from scout.yaml. "
        "The ETag header contains a hash of the file for conditional updates.",
    )
    async def get_project_config() -> Response:
        """Return project configuration with ETag header."""
        config, etag = read_project_config_with_etag()

        return InspectPydanticJSONResponse(
            content=config,
            headers={"ETag": f'"{etag}"'},
        )

    @router.put(
        "/project/config",
        response_model=ProjectConfig,
        response_class=InspectPydanticJSONResponse,
        summary="Update project configuration",
        description="Updates the project configuration in scout.yaml while preserving "
        "comments and formatting. Optionally include If-Match header with current ETag for "
        "optimistic concurrency control. Omit If-Match to force save.",
    )
    async def put_project_config(
        config: ProjectConfig,
        if_match: str | None = Header(
            default=None,
            description="ETag from GET request (optional, omit to force save)",
        ),
    ) -> Response:
        """Update project configuration with comment preservation."""
        # Parse the If-Match header (may be quoted), None means force save
        expected_etag = if_match.strip('"') if if_match else None

        try:
            updated_config, new_etag = write_project_config(config, expected_etag)
        except FileNotFoundError:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail="Project config file (scout.yaml) not found",
            ) from None
        except EtagMismatchError:
            raise HTTPException(
                status_code=HTTP_412_PRECONDITION_FAILED,
                detail="Config file has been modified. Please refresh and try again.",
            ) from None
        except PrerequisiteError as e:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail=str(e),
            ) from None

        await notify_topics(["project-config"])

        return InspectPydanticJSONResponse(
            content=updated_config,
            headers={"ETag": f'"{new_etag}"'},
        )

    return router
