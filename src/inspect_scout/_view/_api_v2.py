"""V2 API orchestrator - creates FastAPI app and includes all routers."""

from pathlib import Path as PathlibPath
from typing import Any

from fastapi import FastAPI
from inspect_ai._util.json import JsonChange
from inspect_ai.event._event import Event
from inspect_ai.model import ChatMessage, Content

from .._llm_scanner.params import LlmScannerParams
from .._transcript.types import Transcript
from .._validation.types import ValidationCase
from ._api_v2_config import create_config_router
from ._api_v2_scanners import create_scanners_router
from ._api_v2_scans import create_scans_router
from ._api_v2_topics import create_topics_router
from ._api_v2_transcripts import create_transcripts_router
from ._api_v2_validations import create_validation_router
from ._openapi import build_openapi_schema
from .invalidationTopics import InvalidationTopic
from .types import ViewConfig

API_VERSION = "2.0.0-alpha"


def v2_api_app(
    view_config: ViewConfig | None = None,
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
    app.include_router(create_config_router(view_config=view_config))
    app.include_router(create_topics_router())
    app.include_router(create_transcripts_router())
    app.include_router(create_scans_router(streaming_batch_size=streaming_batch_size))
    app.include_router(create_scanners_router())
    app.include_router(create_validation_router(PathlibPath.cwd()))

    def custom_openapi() -> dict[str, Any]:
        if not app.openapi_schema:
            app.openapi_schema = build_openapi_schema(
                app,
                extra_schemas=[
                    ("Content", Content),
                    ("ChatMessage", ChatMessage),
                    ("ValidationCase", ValidationCase),
                    ("Event", Event),
                    ("JsonChange", JsonChange),
                    ("LlmScannerParams", LlmScannerParams),
                    ("InvalidationTopic", InvalidationTopic),
                    ("Transcript", Transcript),
                ],
            )
        return app.openapi_schema

    app.openapi = custom_openapi  # type: ignore[method-assign]

    return app
