import base64
from typing import Any

from fastapi.responses import JSONResponse
from inspect_ai._util.json import to_json_safe
from pydantic.json_schema import GenerateJsonSchema, JsonSchemaMode, JsonSchemaValue
from pydantic_core import CoreSchema, core_schema
from typing_extensions import override


class CustomJsonSchemaGenerator(GenerateJsonSchema):
    """Custom JSON schema generator for response-oriented OpenAPI schemas.

    Customizations:
    - Required is determined by nullability, not defaults
      (`str | None` -> optional, `str` -> required even with default)
    - JsonValue generates a proper recursive schema instead of empty {}
    """

    def _is_nullable_schema(self, schema: CoreSchema) -> bool:
        """Check if schema represents a nullable type."""
        schema_type = schema.get("type")
        if schema_type == "nullable":
            return True
        if schema_type == "default":
            return self._is_nullable_schema(schema.get("schema", {}))
        return False

    def field_is_required(
        self,
        field: core_schema.ModelField
        | core_schema.DataclassField
        | core_schema.TypedDictField,
        total: bool,
    ) -> bool:
        schema = field.get("schema", {})
        return not self._is_nullable_schema(schema)

    def generate(
        self, schema: CoreSchema, mode: JsonSchemaMode = "validation"
    ) -> JsonSchemaValue:
        result = super().generate(schema, mode)
        self._fix_json_value_defs(result)
        return result

    def _fix_json_value_defs(self, schema: dict[str, Any]) -> None:
        """Replace empty JsonValue definition with proper JSON schema.

        Uses non-recursive definition since openapi-typescript inlines recursive
        refs, causing TS2502 circular reference errors. Uses additionalProperties: true
        for object to generate Record<string, unknown> instead of Record<string, never>.
        """
        defs = schema.get("$defs", {})
        if "JsonValue" in defs and defs["JsonValue"] == {}:
            defs["JsonValue"] = {
                "oneOf": [
                    {"type": "null"},
                    {"type": "boolean"},
                    {"type": "integer"},
                    {"type": "number"},
                    {"type": "string"},
                    {"type": "array", "items": {}},
                    {"type": "object", "additionalProperties": {}},
                ]
            }


def decode_base64url(s: str) -> str:
    """Decode a base64url-encoded string (restores padding automatically)."""
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4)).decode()


class InspectPydanticJSONResponse(JSONResponse):
    """Like the standard starlette JSON, but allows NaN."""

    @override
    def render(self, content: Any) -> bytes:
        return to_json_safe(content)
