"""Project detection, loading, and global state management."""

import hashlib
import os
import tempfile
from io import StringIO
from pathlib import Path
from typing import Any

from inspect_ai._util.config import read_config_object
from inspect_ai._util.error import PrerequisiteError
from inspect_ai._util.file import file, filesystem
from inspect_ai._util.path import pretty_path
from jsonschema import Draft7Validator
from ruamel.yaml import YAML

from inspect_scout._util.constants import (
    DEFAULT_LOGS_DIR,
    DEFAULT_SCANS_DIR,
    DEFAULT_TRANSCRIPTS_DIR,
)

from .merge import merge_configs
from .types import ProjectConfig
from .yaml_merge import apply_config_update

# Local project override filename
LOCAL_PROJECT_FILENAME = "scout.local.yaml"


def read_project() -> ProjectConfig:
    project_file = Path.cwd() / "scout.yaml"
    if project_file.exists():
        project = load_project_config(project_file)
    else:
        project = create_default_project()

    # provide default transcripts if we need to
    if project.transcripts is None:
        project.transcripts = default_transcripts_dir()

    # provide defaults scans if we need to
    if project.scans is None:
        project.scans = DEFAULT_SCANS_DIR

    return project


def find_local_project_file(project_file: Path) -> Path | None:
    """Find scout.local.yaml in the same directory as scout.yaml.

    Args:
        project_file: Path to the main scout.yaml file.

    Returns:
        Path to scout.local.yaml if it exists, None otherwise.
    """
    local_file = project_file.parent / LOCAL_PROJECT_FILENAME
    return local_file if local_file.exists() else None


def load_project_config(path: Path) -> ProjectConfig:
    """Load and validate project configuration from a scout.yaml file.

    If scout.local.yaml exists in the same directory, it is merged on top
    of the base configuration.

    Uses Draft7Validator for schema validation, following the same pattern
    as scanjob_from_config_file.

    Args:
        path: Path to the scout.yaml file.

    Returns:
        Validated ProjectConfig instance.

    Raises:
        PrerequisiteError: If the configuration is invalid.
    """
    # Load base config
    config = _load_single_config(path)

    # Check for local override
    local_path = find_local_project_file(path)
    if local_path:
        local_config = _load_single_config(local_path)
        config = merge_configs(config, local_config)

    return config


def _load_single_config(path: Path) -> ProjectConfig:
    """Load and validate a single config file.

    Args:
        path: Path to the config file.

    Returns:
        Validated ProjectConfig instance.

    Raises:
        PrerequisiteError: If the configuration is invalid.
    """
    with file(path.as_posix(), "r") as f:
        project_config = read_config_object(f.read())

    # Validate schema before deserializing
    schema = ProjectConfig.model_json_schema(mode="validation")
    validator = Draft7Validator(schema)
    errors = list(validator.iter_errors(project_config))
    if errors:
        message = "\n".join(
            [
                f"Found validation errors parsing config from {pretty_path(path.as_posix())}:"
            ]
            + [f"- {error.message}" for error in errors]
        )
        raise PrerequisiteError(message)

    return ProjectConfig.model_validate(project_config)


def create_default_project() -> ProjectConfig:
    return ProjectConfig(
        transcripts=default_transcripts_dir(),
        scans=DEFAULT_SCANS_DIR,
    )


def default_transcripts_dir() -> str | None:
    if Path(DEFAULT_TRANSCRIPTS_DIR).is_dir():
        return DEFAULT_TRANSCRIPTS_DIR
    else:
        # inspect logs
        inspect_logs = os.environ.get("INSPECT_LOG_DIR", DEFAULT_LOGS_DIR)
        fs = filesystem(inspect_logs)
        if fs.exists(inspect_logs):
            return inspect_logs

    # none found
    return None


def get_project_file_path() -> Path:
    """Get the path to the project configuration file.

    Returns:
        Path to scout.yaml in the current working directory.
    """
    return Path.cwd() / "scout.yaml"


def compute_project_etag(content: str) -> str:
    """Compute an ETag from file content.

    Args:
        content: The file content to hash.

    Returns:
        SHA-256 hash of the content as a hex string.
    """
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def read_project_config_with_etag() -> tuple[ProjectConfig, str]:
    """Read project configuration and compute its ETag.

    Reads the base scout.yaml only (ignores scout.local.yaml).
    If no scout.yaml exists, returns a default config with an etag based on
    what the YAML content would be.

    Returns:
        Tuple of (ProjectConfig, etag).

    Raises:
        PrerequisiteError: If the configuration is invalid.
    """
    project_file = get_project_file_path()

    if not project_file.exists():
        # Return default config with etag based on YAML serialization
        config = create_default_project()
        yaml = YAML()
        yaml.preserve_quotes = True
        output = StringIO()
        config_dict = _clean_empty_values(config.model_dump())
        yaml.dump(config_dict, output)
        etag = compute_project_etag(output.getvalue())
        return config, etag

    content = project_file.read_text(encoding="utf-8")
    etag = compute_project_etag(content)

    # Parse and validate
    config = _load_single_config(project_file)

    return config, etag


class EtagMismatchError(Exception):
    """Raised when the provided ETag does not match the current file."""

    def __init__(self, expected: str, actual: str) -> None:
        super().__init__(f"ETag mismatch: expected {expected}, got {actual}")
        self.expected = expected
        self.actual = actual


def write_project_config(
    config: ProjectConfig,
    expected_etag: str | None = None,
) -> tuple[ProjectConfig, str]:
    """Write project configuration, preserving YAML comments.

    Args:
        config: The new configuration to write.
        expected_etag: The expected ETag of the current file (for optimistic locking).
            If None, skips etag verification (force save).

    Returns:
        Tuple of (updated ProjectConfig, new etag).

    Raises:
        EtagMismatchError: If the current file's ETag doesn't match expected_etag.
        PrerequisiteError: If the configuration is invalid.
    """
    project_file = get_project_file_path()

    yaml = YAML()
    yaml.preserve_quotes = True

    if project_file.exists():
        # Read current content and verify etag (if provided)
        current_content = project_file.read_text(encoding="utf-8")
        current_etag = compute_project_etag(current_content)

        if expected_etag is not None and current_etag != expected_etag:
            raise EtagMismatchError(expected_etag, current_etag)

        # Load with ruamel.yaml to preserve comments
        original_data = yaml.load(current_content)

        # Convert config to dict for merging, excluding None values and empty collections
        config_dict: dict[str, Any] = _clean_empty_values(config.model_dump())

        # Apply updates preserving comments
        apply_config_update(original_data, config_dict)

        # Write to string
        output = StringIO()
        yaml.dump(original_data, output)
        new_content = output.getvalue()
    else:
        # File doesn't exist - create new config
        # Convert config to dict, excluding None values and empty collections
        config_dict = _clean_empty_values(config.model_dump())

        # Write to string
        output = StringIO()
        yaml.dump(config_dict, output)
        new_content = output.getvalue()

    # Atomic write: write to temp file, then rename
    temp_fd, temp_path = tempfile.mkstemp(
        dir=project_file.parent,
        prefix=".scout_",
        suffix=".yaml.tmp",
    )
    try:
        with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
            f.write(new_content)
        os.replace(temp_path, project_file)
    except Exception:
        # Clean up temp file on failure
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        raise

    # Compute new etag and return validated config
    new_etag = compute_project_etag(new_content)
    updated_config = _load_single_config(project_file)

    return updated_config, new_etag


def _clean_empty_values(data: dict[str, Any]) -> dict[str, Any]:
    """Recursively remove None values and empty collections from a dict.

    Used when creating new YAML files to produce cleaner output.
    """
    result: dict[str, Any] = {}
    for key, value in data.items():
        if value is None:
            continue
        elif isinstance(value, dict):
            cleaned = _clean_empty_values(value)
            if cleaned:  # Only include non-empty dicts
                result[key] = cleaned
        elif isinstance(value, list):
            if value:  # Only include non-empty lists
                # Recursively clean list items that are dicts
                cleaned_list = []
                for item in value:
                    if isinstance(item, dict):
                        cleaned_item = _clean_empty_values(item)
                        if cleaned_item:
                            cleaned_list.append(cleaned_item)
                    else:
                        cleaned_list.append(item)
                if cleaned_list:
                    result[key] = cleaned_list
        else:
            result[key] = value
    return result
