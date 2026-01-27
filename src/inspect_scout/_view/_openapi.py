"""OpenAPI schema generation helpers."""

from typing import Any, Literal, Union, get_args, get_origin

from fastapi import FastAPI

from ._server_common import CustomJsonSchemaGenerator


def build_openapi_schema(
    app: FastAPI,
    extra_schemas: list[tuple[str, Any]],
) -> dict[str, Any]:
    """Build customized OpenAPI schema.

    Args:
        app: FastAPI application
        extra_schemas: Additional types to include in schema as (name, type) tuples.
            - Union types: creates oneOf schema with given name, plus member schemas
            - Literal types: creates enum schema
            - Pydantic models: creates schema with given name

    Returns:
        OpenAPI schema dict with 422 responses removed and extra schemas added.
    """
    from fastapi._compat import v2
    from fastapi.openapi.utils import get_openapi

    # Monkey-patch custom schema generator for response-oriented schemas
    v2.GenerateJsonSchema = CustomJsonSchemaGenerator  # type: ignore

    openapi_schema = get_openapi(
        title=app.title, version=app.version, routes=app.routes
    )

    # Remove implied and noisy 422 responses
    for path in openapi_schema.get("paths", {}).values():
        for operation in path.values():
            if isinstance(operation, dict):
                operation.get("responses", {}).pop("422", None)

    # Force additional types into schema even if not referenced by endpoints
    ref_template = "#/components/schemas/{model}"
    schemas = openapi_schema.setdefault("components", {}).setdefault("schemas", {})

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
                schemas[m.__name__] = _schema_without_defs(schema)
            schemas[name] = {
                "oneOf": [
                    {"$ref": f"#/components/schemas/{m.__name__}"} for m in members
                ]
            }
        elif get_origin(t) is Literal:
            # Literal type: create enum schema
            schemas[name] = {"type": "string", "enum": list(get_args(t))}
        elif hasattr(t, "model_json_schema"):
            # Pydantic model: add directly
            schema = t.model_json_schema(
                ref_template=ref_template,
                schema_generator=CustomJsonSchemaGenerator,
            )
            schemas.update(schema.get("$defs", {}))
            schemas[name] = _schema_without_defs(schema)

    return openapi_schema


def _schema_without_defs(schema: dict[str, Any]) -> dict[str, Any]:
    """Return schema dict excluding $defs key."""
    return {k: v for k, v in schema.items() if k != "$defs"}
