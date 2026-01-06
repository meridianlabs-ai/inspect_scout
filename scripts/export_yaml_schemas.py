#!/usr/bin/env python3
"""Export JSON schemas for YAML config files.

Run this script when config models change to regenerate schemas.
The generated schemas are used by VS Code YAML extension for completion/validation.

Usage:
    python scripts/export_yaml_schemas.py [--output-dir DIR]
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def set_additional_properties(schema: dict[str, Any], value: bool = True) -> None:
    """Recursively set additionalProperties on all object definitions.

    This ensures forward compatibility - new fields added to Python models
    won't cause validation errors until the VS Code extension is updated.
    """
    if isinstance(schema, dict):
        # Set additionalProperties on object types (override existing value)
        if schema.get("type") == "object" or "properties" in schema:
            schema["additionalProperties"] = value

        # Recurse into nested structures
        for key, val in schema.items():
            if key == "additionalProperties":
                continue  # Skip, we just set this
            if isinstance(val, dict):
                set_additional_properties(val, value)
            elif isinstance(val, list):
                for item in val:
                    if isinstance(item, dict):
                        set_additional_properties(item, value)

        # Handle $defs (Pydantic 2.x schema definitions)
        if "$defs" in schema:
            for def_schema in schema["$defs"].values():
                set_additional_properties(def_schema, value)


def main() -> None:
    parser = argparse.ArgumentParser(description="Export YAML schemas")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory for schemas (default: ../inspect_vscode/assets/schemas)",
    )
    args = parser.parse_args()

    # Add src to path to import inspect_scout
    repo_root = Path(__file__).parent.parent
    sys.path.insert(0, str(repo_root / "src"))

    try:
        from inspect_scout._project.types import ProjectConfig
        from inspect_scout._scanjob_config import ScanJobConfig
    except ImportError as e:
        print(f"Error: Failed to import inspect_scout: {e}", file=sys.stderr)
        print("Ensure dependencies are installed.", file=sys.stderr)
        sys.exit(1)

    # Determine output directory
    if args.output_dir:
        output_dir = args.output_dir
    else:
        # Default to sibling inspect_vscode repo
        output_dir = repo_root.parent / "inspect_vscode" / "assets" / "schemas"

    output_dir.mkdir(parents=True, exist_ok=True)

    # Export ScanJobConfig schema
    scanjob_schema = ScanJobConfig.model_json_schema(mode="validation")
    scanjob_schema["$schema"] = "http://json-schema.org/draft-07/schema#"
    scanjob_schema["title"] = "Scout Scan Job"
    scanjob_schema.pop("description", None)
    set_additional_properties(scanjob_schema)

    scanjob_path = output_dir / "scanjob.schema.json"
    with scanjob_path.open("w") as f:
        json.dump(scanjob_schema, f, indent=2, sort_keys=True)
        f.write("\n")
    print(f"✓ Exported ScanJobConfig schema to {scanjob_path}")

    # Export ProjectConfig schema
    project_schema = ProjectConfig.model_json_schema(mode="validation")
    project_schema["$schema"] = "http://json-schema.org/draft-07/schema#"
    project_schema["title"] = "Scout Project"
    project_schema.pop("description", None)
    set_additional_properties(project_schema)

    project_path = output_dir / "project.schema.json"
    with project_path.open("w") as f:
        json.dump(project_schema, f, indent=2, sort_keys=True)
        f.write("\n")
    print(f"✓ Exported ProjectConfig schema to {project_path}")


if __name__ == "__main__":
    main()
