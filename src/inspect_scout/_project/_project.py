"""Project detection, loading, and global state management."""

import os
from pathlib import Path

from inspect_ai._util.config import read_config_object
from inspect_ai._util.error import PrerequisiteError
from inspect_ai._util.file import file, filesystem
from inspect_ai._util.path import pretty_path
from jsonschema import Draft7Validator

from inspect_scout._util.constants import (
    DEFAULT_SCANS_DIR,
    DEFAULT_TRANSCRIPTS_DIR,
    DFEAULT_LOGS_DIR,
)

from .merge import merge_configs
from .types import ProjectConfig

# Global project state
_current_project: ProjectConfig | None = None
_project_transcripts: str | None = None
_project_scans: str | None = None

# Local project override filename
LOCAL_PROJECT_FILENAME = "scout.local.yaml"


def init_project(
    *, transcripts: str | None = None, scans: str | None = None
) -> ProjectConfig:
    """Initialize the global project configuration.

    Searches for scout.yaml starting from cwd, walking up the directory tree.
    If no project file is found, creates a default project.

    Always reinitializes (no caching). This is safe because scan_async()
    and view() are never concurrent within a process, and enables multiple
    projects to be used within a single Python script.

    Returns:
        The initialized ProjectConfig.
    """
    global _project_transcripts
    global _project_scans
    _project_transcripts = transcripts
    _project_scans = scans
    return sync_project()


def sync_project() -> ProjectConfig:
    """Update the global project configuration.

    Always reinitializes (no caching). This is safe because scan_async()
    and view() are never concurrent within a process, and enables multiple
    projects to be used within a single Python script.

    Returns:
        The initialized ProjectConfig.
    """
    global _current_project
    global _project_transcripts
    global _project_scans

    project_file = Path.cwd() / "scout.yaml"
    if project_file.exists():
        _current_project = load_project_config(project_file)
    else:
        _current_project = create_default_project()

    # override transcripts ans scans if requested
    if _project_transcripts is not None:
        _current_project.transcripts = _project_transcripts
    if _project_scans is not None:
        _current_project.scans = _project_scans

    # provide default transcripts if we need to
    if _current_project.transcripts is None:
        _current_project.transcripts = default_transcripts_dir()

    # provide defaults scans if we need to
    if _current_project.scans is None:
        _current_project.scans = DEFAULT_SCANS_DIR

    return _current_project


def project() -> ProjectConfig:
    """Get the current project configuration.

    Returns:
        The current ProjectConfig.

    Raises:
        RuntimeError: If project has not been initialized.
    """
    if _current_project is None:
        raise RuntimeError("Project not initialized. Call init_project() first.")
    return _current_project


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
        inspect_logs = os.environ.get("INSPECT_LOG_DIR", DFEAULT_LOGS_DIR)
        fs = filesystem(inspect_logs)
        if fs.exists(inspect_logs):
            return inspect_logs

    # none found
    return None
