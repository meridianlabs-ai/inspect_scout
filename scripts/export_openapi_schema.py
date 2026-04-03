#!/usr/bin/env python3
"""Export OpenAPI schema and regenerate TypeScript types.

Stub endpoints pull scout-specific type dependency trees into the schema.
RootModel wrappers give stable names to literals. Inspect-originated types
(Content, ChatMessage, Event, JsonChange, etc.) are NOT included here —
the TS side imports those from @tsmono/inspect-common.

Usage:
    python scripts/export_openapi_schema.py
"""

import json
import os
import subprocess
import sys
from pathlib import Path

from pydantic import RootModel


def main() -> None:
    # Add src to path to import inspect_scout
    repo_root = Path(__file__).parent.parent
    sys.path.insert(0, str(repo_root / "src"))

    from inspect_ai._view._openapi import build_openapi_schema
    from inspect_scout._llm_scanner.params import LlmScannerParams
    from inspect_scout._transcript.types import Transcript
    from inspect_scout._validation.types import ValidationCase
    from inspect_scout._view._api_v2 import v2_api_app
    from inspect_scout._view._api_v2_transcripts import (
        RawEncoding as _RawEncoding,
    )
    from inspect_scout._view.invalidationTopics import (
        InvalidationTopic as _InvalidationTopic,
    )

    # RootModel wrappers give stable schema names to literals.
    class InvalidationTopic(RootModel[_InvalidationTopic]):
        pass

    class RawEncoding(RootModel[_RawEncoding]):
        pass

    # Create the real app, then add stub endpoints for scout-specific types.
    app = v2_api_app()

    @app.get("/schema/validation-case")
    def _validation_case() -> ValidationCase:
        raise NotImplementedError

    @app.get("/schema/llm-scanner-params")
    def _llm_scanner_params() -> LlmScannerParams:
        raise NotImplementedError

    @app.get("/schema/invalidation-topic")
    def _invalidation_topic() -> InvalidationTopic:
        raise NotImplementedError

    @app.get("/schema/transcript")
    def _transcript() -> Transcript:
        raise NotImplementedError

    @app.get("/schema/raw-encoding")
    def _raw_encoding() -> RawEncoding:
        raise NotImplementedError

    schema = build_openapi_schema(app)

    # Write to _view/openapi.json (read by the TS monorepo's generate-types script)
    output_path = repo_root / "src/inspect_scout/_view/openapi.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w") as f:
        json.dump(schema, f, indent=2, sort_keys=True)
        f.write("\n")

    print(f"✓ Exported OpenAPI schema to {output_path.relative_to(repo_root)}")

    # Regenerate TypeScript types from the updated schema
    ts_mono_dir = os.path.abspath(
        (repo_root / "src/inspect_scout/_view/ts-mono").as_posix()
    )
    subprocess.run(
        ["pnpm", "--filter", "scout", "types:generate"],
        cwd=ts_mono_dir,
        check=True,
    )


if __name__ == "__main__":
    main()
