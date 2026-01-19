"""Git-related utilities."""

import subprocess
from pathlib import Path


def get_git_files(project_dir: Path) -> set[Path] | None:
    """Get all non-ignored files in a git repository.

    Uses `git ls-files` to efficiently list all tracked and untracked
    (but not ignored) files in a single call.

    Args:
        project_dir: The root directory of the git repository.

    Returns:
        Set of absolute Path objects for non-ignored files, or None if
        not a git repo or git is unavailable.
    """
    try:
        # Get tracked files and untracked files (excluding ignored)
        result = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
            cwd=str(project_dir),
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return None

        files = set()
        for line in result.stdout.splitlines():
            if line.strip():
                files.add((project_dir / line).resolve())
        return files

    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None
