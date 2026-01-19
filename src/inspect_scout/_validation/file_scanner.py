"""Scan for validation files in a project directory."""

from collections.abc import Iterator
from pathlib import Path

from .._util.git import get_git_files
from .._util.venv import is_in_venv, is_venv_directory

# Directories to always exclude from scanning
EXCLUDED_DIRS = frozenset(
    {
        ".git",
        "__pycache__",
        "node_modules",
        ".venv",
        "venv",
        "env",
        ".env",
        ".tox",
        ".nox",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "dist",
        "build",
        "*.egg-info",
    }
)

# Valid validation file extensions
VALIDATION_EXTENSIONS = frozenset({".csv", ".yaml", ".yml", ".json", ".jsonl"})


def is_validation_file(path: Path) -> bool:
    """Check if a file is a valid validation file.

    A validation file must:
    1. Have a supported extension (.csv, .yaml, .yml, .json, .jsonl)
    2. Contain an 'id' column
    3. Contain either 'target', 'target_*' columns, or 'label_*' columns
    """
    if not path.is_file():
        return False

    suffix = path.suffix.lower()
    if suffix not in VALIDATION_EXTENSIONS:
        return False

    try:
        # Import here to avoid circular imports
        from .writer import _load_raw_data

        cases, _ = _load_raw_data(path)
        if not cases:
            return False

        # Check the first case for required columns
        first_case = cases[0]
        if not isinstance(first_case, dict):
            return False

        # Must have 'id' key
        if "id" not in first_case:
            return False

        # Must have target or labels
        has_target = "target" in first_case
        has_target_cols = any(k.startswith("target_") for k in first_case)
        has_label_cols = any(k.startswith("label_") for k in first_case)

        return has_target or has_target_cols or has_label_cols

    except Exception:
        # If we can't read or parse the file, it's not a valid validation file
        return False


def _is_in_excluded_path(path: Path) -> bool:
    """Check if a path is within an excluded directory."""
    parts = path.parts
    for part in parts:
        # Skip hidden directories
        if part.startswith("."):
            return True
        # Skip common excluded directories
        if part in EXCLUDED_DIRS:
            return True
    return False


def scan_validation_files(project_dir: Path) -> Iterator[Path]:
    """Scan a project directory for validation files.

    Yields paths to validation files, excluding:
    - Hidden directories (starting with '.')
    - Common excluded directories (node_modules, __pycache__, etc.)
    - Python virtual environments
    - Git-ignored paths

    Uses `git ls-files` for efficient git-ignore handling (single call)
    instead of checking each file individually.

    Args:
        project_dir: The root directory to scan.

    Yields:
        Path objects for each validation file found.
    """
    project_dir = project_dir.resolve()

    # Try to get non-ignored files from git (single call, much faster)
    git_files = get_git_files(project_dir)

    if git_files is not None:
        # Git repo: iterate over non-ignored files from git
        for file_path in git_files:
            # Skip files outside project_dir (shouldn't happen, but be safe)
            try:
                file_path.relative_to(project_dir)
            except ValueError:
                continue

            # Skip files in excluded directories
            rel_path = file_path.relative_to(project_dir)
            if _is_in_excluded_path(rel_path):
                continue

            # Skip files in virtual environments
            if is_in_venv(file_path):
                continue

            # Check if it's a validation file
            if is_validation_file(file_path):
                yield file_path
    else:
        # Not a git repo or git unavailable: fall back to directory walk
        yield from _scan_directory_no_git(project_dir)


def _scan_directory_no_git(project_dir: Path) -> Iterator[Path]:
    """Scan directory without git support (fallback for non-git repos)."""

    def should_skip_dir(dir_path: Path) -> bool:
        """Check if a directory should be skipped."""
        name = dir_path.name

        # Skip hidden directories
        if name.startswith("."):
            return True

        # Skip common excluded directories
        if name in EXCLUDED_DIRS:
            return True

        # Skip if it matches a glob pattern in EXCLUDED_DIRS
        for pattern in EXCLUDED_DIRS:
            if "*" in pattern and dir_path.match(pattern):
                return True

        # Skip virtual environments
        if is_venv_directory(dir_path):
            return True

        return False

    def scan_directory(dir_path: Path) -> Iterator[Path]:
        """Recursively scan a directory for validation files."""
        try:
            entries = list(dir_path.iterdir())
        except PermissionError:
            return

        for entry in entries:
            if entry.is_dir():
                if not should_skip_dir(entry):
                    yield from scan_directory(entry)
            elif entry.is_file():
                # Check if it's a validation file
                if is_validation_file(entry):
                    yield entry

    yield from scan_directory(project_dir)
