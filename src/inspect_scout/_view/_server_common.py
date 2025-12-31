import base64
from typing import Any

from fastapi.responses import JSONResponse
from inspect_ai._util.json import to_json_safe
from pydantic.json_schema import GenerateJsonSchema
from pydantic_core import CoreSchema, core_schema
from typing_extensions import override
from upath import UPath


class NullableIsOptionalJsonSchema(GenerateJsonSchema):
    """Required is determined by nullability, not by presence of defaults.

    - `str | None` -> optional (even without default)
    - `str` -> required (even with default)
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


def decode_base64url(s: str) -> str:
    """Decode a base64url-encoded string (restores padding automatically)."""
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4)).decode()


class InspectPydanticJSONResponse(JSONResponse):
    """Like the standard starlette JSON, but allows NaN."""

    @override
    def render(self, content: Any) -> bytes:
        return to_json_safe(content)


async def default_transcripts_dir() -> str:
    """Return resolved path to transcripts dir, scrounging scan results for a plausible default."""
    return (
        UPath(await _scrounged_transcripts_dir() or "file://./transcripts")
        .resolve()
        .as_posix()
    )


async def _scrounged_transcripts_dir() -> str | None:
    # TODO: Scrounge any scan results to find a plausible transcript dir
    return None
