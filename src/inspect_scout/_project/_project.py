"""Project detection, loading, and global state management."""

from pathlib import Path

from inspect_ai._util.config import read_config_object
from inspect_ai._util.error import PrerequisiteError
from inspect_ai._util.file import file
from inspect_ai._util.path import pretty_path
from jsonschema import Draft7Validator

from .types import ProjectConfig

# Global project state
_current_project: ProjectConfig | None = None


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


def init_project() -> ProjectConfig:
    """Initialize the global project configuration.

    Searches for scout.yaml starting from cwd, walking up the directory tree.
    If no project file is found, creates a default project.

    Always reinitializes (no caching). This is safe because scan_async()
    and view() are never concurrent within a process, and enables multiple
    projects to be used within a single Python script.

    Returns:
        The initialized ProjectConfig.
    """
    global _current_project

    project_file = find_project_file(Path.cwd())
    if project_file:
        _current_project = load_project_config(project_file)
    else:
        _current_project = create_default_project()

    return _current_project


def find_project_file(start_dir: Path) -> Path | None:
    """Find scout.yaml by walking up from start_dir.

    Stops at git repo root (if in a repo) or filesystem root.

    Args:
        start_dir: Directory to start searching from.

    Returns:
        Path to scout.yaml if found, None otherwise.
    """
    git_root = find_git_root(start_dir)
    current = start_dir.resolve()

    while True:
        project_file = current / "scout.yaml"
        if project_file.exists():
            return project_file

        # Stop if we've reached git root or filesystem root
        if git_root and current == git_root:
            return None
        if current == current.parent:  # Cross-platform root detection
            return None

        current = current.parent


def load_project_config(path: Path) -> ProjectConfig:
    """Load and validate project configuration from a scout.yaml file.

    Uses Draft7Validator for schema validation, following the same pattern
    as scanjob_from_config_file.

    Args:
        path: Path to the scout.yaml file.

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
                f"Found validation errors parsing project config from {pretty_path(path.as_posix())}:"
            ]
            + [f"- {error.message}" for error in errors]
        )
        raise PrerequisiteError(message)

    config = ProjectConfig.model_validate(project_config)

    # Default name to directory name if not specified
    if config.name == "job":  # default from ScanJobConfig
        config = config.model_copy(update={"name": path.parent.name})

    return config


def create_default_project() -> ProjectConfig:
    """Create default project configuration.

    Checks for standard transcript locations in order:
    1. ./transcripts
    2. ./logs

    Returns:
        Default ProjectConfig with results="./scans" and detected transcripts.
    """
    if Path("./transcripts").is_dir():
        transcripts: str | None = "./transcripts"
    elif Path("./logs").is_dir():
        transcripts = "./logs"
    else:
        transcripts = None

    return ProjectConfig(
        name=Path.cwd().name,
        scans="./scans",
        transcripts=transcripts,
    )


def find_git_root(path: Path) -> Path | None:
    """Find git repository root by looking for .git directory.

    Args:
        path: Starting path to search from.

    Returns:
        Path to git root if found, None otherwise.
    """
    current = path.resolve()
    while current != current.parent:  # Cross-platform root detection
        if (current / ".git").exists():
            return current
        current = current.parent
    return None
