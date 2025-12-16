from typing import Any

from fastapi.responses import JSONResponse
from inspect_ai._util.json import to_json_safe
from typing_extensions import override


class InspectPydanticJSONResponse(JSONResponse):
    """Like the standard starlette JSON, but allows NaN."""

    @override
    def render(self, content: Any) -> bytes:
        return to_json_safe(content)
