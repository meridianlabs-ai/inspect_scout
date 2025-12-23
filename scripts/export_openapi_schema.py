#!/usr/bin/env python3
"""Export OpenAPI schema from FastAPI app to JSON file.

Run this script when API models change to regenerate the OpenAPI schema.
The generated openapi.json is used by TypeScript build to generate types.

Usage:
    python scripts/export_openapi_schema.py
"""

import json
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

    # Write to www/openapi.json
    output_path = repo_root / "src/inspect_scout/_view/www/openapi.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w") as f:
        json.dump(schema, f, indent=2, sort_keys=True)
        f.write("\n")  # Add trailing newline

    print(f"✓ Exported OpenAPI schema to {output_path.relative_to(repo_root)}")


if __name__ == "__main__":
    main()
