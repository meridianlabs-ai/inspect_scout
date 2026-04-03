import base64
from typing import Any

from fastapi.responses import JSONResponse
from inspect_ai._util.json import to_json_safe
from typing_extensions import override


def decode_base64url(s: str) -> str:
    """Decode a base64url-encoded string (restores padding automatically)."""
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4)).decode()


class InspectPydanticJSONResponse(JSONResponse):
    """Like the standard starlette JSON, but allows NaN."""

    @override
    def render(self, content: Any) -> bytes:
        return to_json_safe(content)
