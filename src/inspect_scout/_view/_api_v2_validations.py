"""Validation Sets REST API endpoints."""

import json
from pathlib import Path
from typing import Any, cast

from fastapi import APIRouter, HTTPException
from fastapi import Path as PathParam
from send2trash import send2trash
from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
)
from upath import UPath

from .._validation.file_scanner import scan_validation_files
from .._validation.predicates import PredicateType
from .._validation.types import ValidationCase
from .._validation.writer import ValidationFileWriter, _unflatten_labels
from ._api_v2_types import (
    CreateValidationSetRequest,
    RenameValidationSetRequest,
    ValidationCaseRequest,
)
from ._server_common import InspectPydanticJSONResponse, decode_base64url


def create_validation_router(
    project_dir: Path,
) -> APIRouter:
    """Create a validation API router.

    Args:
        project_dir: The project directory for scanning and path validation.

    Returns:
        Configured APIRouter with validation endpoints.
    """
    router = APIRouter(prefix="/validations", tags=["validations"])
    project_dir = project_dir.resolve()

    @router.get(
        "",
        response_class=InspectPydanticJSONResponse,
        summary="List validation files",
        description="Scans the project directory for validation files (.csv, .yaml, .json, .jsonl) "
        "and returns their URIs.",
    )
    async def list_validations() -> list[str]:
        """List all validation files in the project."""
        paths: list[str] = []

        for file_path in scan_validation_files(project_dir):
            try:
                uri = UPath(file_path).resolve().as_uri()
                paths.append(uri)
            except Exception:
                # Skip files that can't be processed
                continue

        return paths

    @router.post(
        "",
        response_class=InspectPydanticJSONResponse,
        summary="Create a validation file",
        description="Creates a new validation file at the specified path with optional initial cases. "
        "Returns the URI of the created file.",
    )
    async def create_validation(body: CreateValidationSetRequest) -> str:
        """Create a new validation file."""
        # Convert URI to path
        file_path = _uri_to_path(body.path)

        # Validate path is within project directory
        _validate_path_within_project(file_path, project_dir)

        # Convert request cases to ValidationCase objects
        cases: list[ValidationCase] = []
        for i, case_req in enumerate(body.cases):
            # Validate that id is provided
            if case_req.id is None:
                raise HTTPException(
                    status_code=HTTP_400_BAD_REQUEST,
                    detail=f"Case {i}: 'id' is required",
                )

            # Validate that exactly one of target or labels is provided
            if case_req.target is None and case_req.labels is None:
                raise HTTPException(
                    status_code=HTTP_400_BAD_REQUEST,
                    detail=f"Case {i}: must specify either 'target' or 'labels'",
                )
            if case_req.target is not None and case_req.labels is not None:
                raise HTTPException(
                    status_code=HTTP_400_BAD_REQUEST,
                    detail=f"Case {i}: cannot specify both 'target' and 'labels'",
                )

            cases.append(
                ValidationCase(
                    id=case_req.id,
                    target=case_req.target,
                    labels=case_req.labels,
                    split=case_req.split,
                    predicate=cast(PredicateType | None, case_req.predicate),
                )
            )

        try:
            ValidationFileWriter.create_new(file_path, cases)
            return UPath(file_path).resolve().as_uri()
        except FileExistsError:
            raise HTTPException(
                status_code=HTTP_409_CONFLICT,
                detail=f"File already exists: {body.path}",
            ) from None

    @router.get(
        "/{uri}",
        response_class=InspectPydanticJSONResponse,
        summary="Get validation cases",
        description="Returns all cases from a validation file.",
    )
    async def get_validation_cases(
        uri: str = PathParam(description="Validation file URI (base64url-encoded)"),
    ) -> list[dict[str, Any]]:
        """Get all cases from a validation file."""
        file_uri = decode_base64url(uri)
        file_path = _uri_to_path(file_uri)

        # Validate path is within project directory
        _validate_path_within_project(file_path, project_dir)

        try:
            writer = ValidationFileWriter(file_path)
            cases = writer.read_cases()
            # Convert label_* columns to nested labels object for API response
            return _unflatten_labels(cases)
        except FileNotFoundError:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail="Validation file not found",
            ) from None

    @router.delete(
        "/{uri}",
        summary="Delete a validation file",
        description="Deletes a validation file from the project.",
    )
    async def delete_validation(
        uri: str = PathParam(description="Validation file URI (base64url-encoded)"),
    ) -> dict[str, bool]:
        """Delete a validation file."""
        file_uri = decode_base64url(uri)
        file_path = _uri_to_path(file_uri)

        # Validate path is within project directory
        _validate_path_within_project(file_path, project_dir)

        if not file_path.exists():
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail="Validation file not found",
            )

        send2trash(str(file_path))
        return {"deleted": True}

    @router.put(
        "/{uri}/rename",
        response_class=InspectPydanticJSONResponse,
        summary="Rename a validation file",
        description="Renames a validation file. Returns the new URI.",
    )
    async def rename_validation(
        body: RenameValidationSetRequest,
        uri: str = PathParam(description="Validation file URI (base64url-encoded)"),
    ) -> str:
        """Rename a validation file."""
        file_uri = decode_base64url(uri)
        file_path = _uri_to_path(file_uri)

        # Validate path is within project directory
        _validate_path_within_project(file_path, project_dir)

        if not file_path.exists():
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail="Validation file not found",
            )

        # Validate new name
        new_name = body.name.strip()
        if not new_name:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail="Name cannot be empty",
            )

        # Check for invalid characters in filename
        invalid_chars = ["/", "\\", ":", "*", "?", '"', "<", ">", "|"]
        if any(c in new_name for c in invalid_chars):
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail=f"Name contains invalid characters: {invalid_chars}",
            )

        # Construct new path with same extension
        extension = file_path.suffix
        new_path = file_path.parent / f"{new_name}{extension}"

        # Validate new path is within project directory
        _validate_path_within_project(new_path, project_dir)

        # Check if target already exists
        if new_path.exists():
            raise HTTPException(
                status_code=HTTP_409_CONFLICT,
                detail=f"A file with the name '{new_name}{extension}' already exists",
            )

        try:
            file_path.rename(new_path)
            return UPath(new_path).resolve().as_uri()
        except OSError as e:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail=f"Failed to rename file: {e}",
            ) from None

    @router.get(
        "/{uri}/{case_id}",
        response_class=InspectPydanticJSONResponse,
        summary="Get a specific case",
        description="Returns a specific case from a validation file by ID.",
    )
    async def get_validation_case(
        uri: str = PathParam(description="Validation file URI (base64url-encoded)"),
        case_id: str = PathParam(description="Case ID (base64url-encoded)"),
    ) -> dict[str, Any]:
        """Get a specific case by ID."""
        file_uri = decode_base64url(uri)
        file_path = _uri_to_path(file_uri)
        decoded_case_id = _decode_case_id(case_id)

        # Validate path is within project directory
        _validate_path_within_project(file_path, project_dir)

        try:
            writer = ValidationFileWriter(file_path)
            cases = writer.read_cases()
            index = writer.find_case_index(cases, decoded_case_id)

            if index is None:
                raise HTTPException(
                    status_code=HTTP_404_NOT_FOUND,
                    detail="Case not found",
                )

            return cases[index]
        except FileNotFoundError:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail="Validation file not found",
            ) from None

    @router.post(
        "/{uri}/{case_id}",
        response_class=InspectPydanticJSONResponse,
        summary="Create or update a case",
        description="Creates or updates a case in a validation file. If the case ID exists, "
        "it will be updated; otherwise, a new case will be created.",
    )
    async def upsert_validation_case(
        body: ValidationCaseRequest,
        uri: str = PathParam(description="Validation file URI (base64url-encoded)"),
        case_id: str = PathParam(description="Case ID (base64url-encoded)"),
    ) -> dict[str, Any]:
        """Create or update a case."""
        file_uri = decode_base64url(uri)
        file_path = _uri_to_path(file_uri)
        decoded_case_id = _decode_case_id(case_id)

        # Validate path is within project directory
        _validate_path_within_project(file_path, project_dir)

        # Validate that exactly one of target or labels is provided
        if body.target is None and body.labels is None:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail="Must specify either 'target' or 'labels'",
            )
        if body.target is not None and body.labels is not None:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail="Cannot specify both 'target' and 'labels'",
            )

        try:
            writer = ValidationFileWriter(file_path)

            # Create ValidationCase object
            case = ValidationCase(
                id=decoded_case_id,
                target=body.target,
                labels=body.labels,
                split=body.split,
                predicate=cast(PredicateType | None, body.predicate),
            )

            writer.upsert_case(case)

            # Return the upserted case
            return case.model_dump(exclude_none=True)
        except FileNotFoundError:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail="Validation file not found",
            ) from None

    @router.delete(
        "/{uri}/{case_id}",
        summary="Delete a case",
        description="Deletes a case from a validation file.",
    )
    async def delete_validation_case(
        uri: str = PathParam(description="Validation file URI (base64url-encoded)"),
        case_id: str = PathParam(description="Case ID (base64url-encoded)"),
    ) -> dict[str, bool]:
        """Delete a case from a validation file."""
        file_uri = decode_base64url(uri)
        file_path = _uri_to_path(file_uri)
        decoded_case_id = _decode_case_id(case_id)

        # Validate path is within project directory
        _validate_path_within_project(file_path, project_dir)

        try:
            writer = ValidationFileWriter(file_path)
            deleted = writer.delete_case(decoded_case_id)

            if not deleted:
                raise HTTPException(
                    status_code=HTTP_404_NOT_FOUND,
                    detail="Case not found",
                )

            return {"deleted": True}
        except FileNotFoundError:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail="Validation file not found",
            ) from None

    return router


def _decode_case_id(encoded_id: str) -> str | list[str]:
    """Decode a base64url-encoded case ID.

    Returns either a string or a list of strings (for composite IDs).
    """
    decoded = decode_base64url(encoded_id)

    # Check if it's a JSON array
    if decoded.startswith("[") and decoded.endswith("]"):
        try:
            parsed = json.loads(decoded)
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            pass

    return decoded


def _validate_path_within_project(path: Path, project_dir: Path) -> None:
    """Validate that a path is within the project directory.

    Raises HTTPException with 400 status if path traversal is detected.
    """
    try:
        resolved = path.resolve()
        project_resolved = project_dir.resolve()

        # Check that the path is within project_dir
        resolved.relative_to(project_resolved)
    except ValueError:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail="Path must be within project directory",
        ) from None


def _uri_to_path(uri: str) -> Path:
    """Convert a file URI to a Path object."""
    from urllib.parse import unquote

    unquoted = unquote(uri)
    if unquoted.startswith("file://"):
        # Handle file:// URIs
        return Path(UPath(unquoted).path)
    return Path(unquoted)
