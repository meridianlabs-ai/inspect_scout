"""Project detection, loading, and global state management."""

import os
from pathlib import Path

from inspect_ai._util.config import read_config_object
from inspect_ai._util.error import PrerequisiteError
from inspect_ai._util.file import file, filesystem
from inspect_ai._util.path import pretty_path
from jsonschema import Draft7Validator

from inspect_scout._util.constants import (
    DEFAULT_LOGS_DIR,
    DEFAULT_SCANS_DIR,
    DEFAULT_TRANSCRIPTS_DIR,
)

from .merge import merge_configs
from .types import ProjectConfig

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

    # Default name to directory name if not specified
    if config.name == "job":  # default from ScanJobConfig
        config = config.model_copy(update={"name": path.parent.name})

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
        name=Path.cwd().name,
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
