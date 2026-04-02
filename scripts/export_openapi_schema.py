#!/usr/bin/env python3
"""Export OpenAPI schema and regenerate TypeScript types.

Run this script when API models change to regenerate the OpenAPI schema
and TypeScript types together.

Usage:
    python scripts/export_openapi_schema.py
"""

import json
import os
import subprocess
import sys
from pathlib import Path


def main() -> None:
    # Add src to path to import inspect_scout
    repo_root = Path(__file__).parent.parent
    sys.path.insert(0, str(repo_root / "src"))

    try:
        from inspect_scout._view._api_v2 import v2_api_app
    except ImportError as e:
        print(f"Error: Failed to import inspect_scout: {e}", file=sys.stderr)
        print("Ensure dependencies are installed.", file=sys.stderr)
        sys.exit(1)

    # Create app and get OpenAPI schema
    app = v2_api_app()
    schema = app.openapi()

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
