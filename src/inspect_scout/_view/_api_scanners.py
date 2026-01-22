"""Scanners REST API endpoints."""

import inspect
from functools import reduce
from typing import Any, Callable, cast

from fastapi import APIRouter
from inspect_ai._util.registry import registry_find, registry_info
from inspect_ai.util import json_schema

from .._query import Condition, condition_as_sql
from ._api_v2_types import ScannerInfo, ScannerParam, ScannersResponse
from ._server_common import InspectPydanticJSONResponse


def create_scanners_router() -> APIRouter:
    """Create scanners API router.

    Returns:
        Configured APIRouter with scanners endpoints.
    """
    router = APIRouter(tags=["scanners"])

    @router.get(
        "/scanners",
        response_model=ScannersResponse,
        response_class=InspectPydanticJSONResponse,
        summary="List available scanners",
        description="Returns info about all registered scanners.",
    )
    async def scanners() -> ScannersResponse:
        """Return info about all registered scanner factories."""

        def param_schema(p: inspect.Parameter) -> dict[str, Any]:
            if p.annotation == inspect.Parameter.empty:
                return {"type": "any"}
            return json_schema(p.annotation).model_dump(exclude_none=True)

        scanner_objs = registry_find(lambda info: info.type == "scanner")
        items = [
            ScannerInfo(
                name=registry_info(s).name,
                version=registry_info(s).metadata.get("scanner_version", 0),
                description=s.__doc__.split("\n")[0] if s.__doc__ else None,
                params=[
                    ScannerParam(
                        name=p.name,
                        schema=param_schema(p),
                        required=p.default == inspect.Parameter.empty,
                        default=(
                            p.default if p.default != inspect.Parameter.empty else None
                        ),
                    )
                    for p in inspect.signature(
                        cast(Callable[..., Any], s)
                    ).parameters.values()
                ],
            )
            for s in scanner_objs
        ]
        return ScannersResponse(items=items)

    @router.post(
        "/code",
        summary="Code endpoint",
    )
    async def code(
        body: Condition | list[Condition],
    ) -> dict[str, str]:
        """Process condition."""
        filter_sql = condition_as_sql(
            reduce(lambda a, b: a & b, body) if isinstance(body, list) else body,
            "filter",
        )
        return {
            "python": f"transcripts.where({filter_sql!r})",
            "filter": filter_sql,
        }

    return router
