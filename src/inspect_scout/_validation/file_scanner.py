"""Scan for validation files in a project directory."""

from collections.abc import Iterator
from pathlib import Path

from .._util.venv import is_venv_directory

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

        _, _, is_valid = _load_raw_data(path)
        return is_valid

    except Exception:
        # If we can't read or parse the file, it's not a valid validation file
        return False


def scan_validation_files(project_dir: Path) -> Iterator[Path]:
    """Scan a project directory for validation files.

    Walks the filesystem under `project_dir`, skipping:
    - Hidden directories (starting with '.')
    - Common excluded directories (node_modules, __pycache__, etc.)
    - Python virtual environments

    `.gitignore` is intentionally NOT consulted: validation sets are often
    user-created data files matching common ignore patterns (e.g. `*.csv`)
    and must remain discoverable regardless of git state.

    Args:
        project_dir: The root directory to scan.

    Yields:
        Path objects for each validation file found.
    """
    yield from _walk(project_dir.resolve())


def _should_skip_dir(dir_path: Path) -> bool:
    name = dir_path.name

    if name.startswith("."):
        return True

    if name in EXCLUDED_DIRS:
        return True

    for pattern in EXCLUDED_DIRS:
        if "*" in pattern and dir_path.match(pattern):
            return True

    if is_venv_directory(dir_path):
        return True

    return False


def _walk(dir_path: Path) -> Iterator[Path]:
    try:
        entries = list(dir_path.iterdir())
    except PermissionError:
        return

    for entry in entries:
        if entry.is_dir():
            if not _should_skip_dir(entry):
                yield from _walk(entry)
        elif entry.is_file():
            if is_validation_file(entry):
                yield entry
