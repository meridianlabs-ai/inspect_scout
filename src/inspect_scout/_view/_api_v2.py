"""V2 API orchestrator - creates FastAPI app and includes all routers."""

from pathlib import Path as PathlibPath
from typing import Any, Union, get_args, get_origin

from fastapi import FastAPI
from inspect_ai._util.file import FileSystem
from inspect_ai._util.json import JsonChange
from inspect_ai._view.fastapi_server import AccessPolicy
from inspect_ai.event._event import Event
from inspect_ai.model import ChatMessage, Content

from .._llm_scanner.params import LlmScannerParams
from .._validation.types import ValidationCase
from ._api_config import create_config_router
from ._api_scanners import create_scanners_router
from ._api_scans import create_scans_router
from ._api_transcripts import create_transcripts_router
from ._api_validations import create_validation_router
from ._server_common import CustomJsonSchemaGenerator
from .types import ViewConfig

API_VERSION = "2.0.0-alpha"


def v2_api_app(
    view_config: ViewConfig | None = None,
    access_policy: AccessPolicy | None = None,
    results_dir: str | None = None,
    fs: FileSystem | None = None,
    streaming_batch_size: int = 1024,
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

    # Remove implied and noisy 422 responses from OpenAPI schema
    def custom_openapi() -> dict[str, Any]:
        if not app.openapi_schema:
            from fastapi._compat import v2
            from fastapi.openapi.utils import get_openapi

            # Monkey-patch custom schema generator for response-oriented schemas
            v2.GenerateJsonSchema = CustomJsonSchemaGenerator  # type: ignore

            openapi_schema = get_openapi(
                title=app.title,
                version=app.version,
                routes=app.routes,
            )
            for path in openapi_schema.get("paths", {}).values():
                for operation in path.values():
                    if isinstance(operation, dict):
                        operation.get("responses", {}).pop("422", None)

            # Force additional types into schema even if not referenced by endpoints.
            # Format: list of (schema_name, type) tuples.
            # - For Union types (type aliases): creates a oneOf schema with the
            #   given name, plus schemas for each member type. Python type aliases
            #   don't preserve their name at runtime, so we must provide it explicitly.
            # - For Pydantic models: creates a schema with the given name.
            extra_schemas = [
                ("Content", Content),
                ("ChatMessage", ChatMessage),
                ("ValidationCase", ValidationCase),
                ("Event", Event),
                ("JsonChange", JsonChange),
                ("LlmScannerParams", LlmScannerParams),
            ]
            ref_template = "#/components/schemas/{model}"
            schemas = openapi_schema.setdefault("components", {}).setdefault(
                "schemas", {}
            )
            for name, t in extra_schemas:
                if get_origin(t) is Union:
                    # Union type: create oneOf schema and add member schemas
                    members = get_args(t)
                    for m in members:
                        schema = m.model_json_schema(
                            ref_template=ref_template,
                            schema_generator=CustomJsonSchemaGenerator,
                        )
                        schemas.update(schema.get("$defs", {}))
                        schemas[m.__name__] = {
                            k: v for k, v in schema.items() if k != "$defs"
                        }
                    schemas[name] = {
                        "oneOf": [
                            {"$ref": f"#/components/schemas/{m.__name__}"}
                            for m in members
                        ]
                    }
                elif hasattr(t, "model_json_schema"):
                    # Pydantic model: add directly
                    schema = t.model_json_schema(
                        ref_template=ref_template,
                        schema_generator=CustomJsonSchemaGenerator,
                    )
                    schemas.update(schema.get("$defs", {}))
                    schemas[name] = {k: v for k, v in schema.items() if k != "$defs"}

            app.openapi_schema = openapi_schema
        return app.openapi_schema

    app.openapi = custom_openapi  # type: ignore[method-assign]

    # Include all routers
    app.include_router(create_config_router(view_config=view_config))
    app.include_router(create_transcripts_router(access_policy=access_policy))
    app.include_router(
        create_scans_router(
            access_policy=access_policy,
            results_dir=results_dir,
            fs=fs,
            streaming_batch_size=streaming_batch_size,
        )
    )
    app.include_router(create_scanners_router())
    app.include_router(create_validation_router(PathlibPath.cwd(), access_policy))

    return app
