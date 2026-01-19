"""Virtual environment detection utilities."""

from pathlib import Path


def is_venv_directory(path: Path) -> bool:
    """Check if a directory is a Python virtual environment or conda environment.

    Detects:
    - Python venvs (pyvenv.cfg file present)
    - virtualenv environments (bin/activate or Scripts/activate.bat)
    - Conda environments (conda-meta/ directory present)

    Args:
        path: Path to check.

    Returns:
        True if the path is a virtual environment directory.
    """
    if not path.is_dir():
        return False

    # Check for pyvenv.cfg (standard venv marker)
    if (path / "pyvenv.cfg").exists():
        return True

    # Check for virtualenv markers
    if (path / "bin" / "activate").exists():
        return True
    if (path / "Scripts" / "activate.bat").exists():  # Windows
        return True

    # Check for conda environment marker
    if (path / "conda-meta").is_dir():
        return True

    return False


def is_in_venv(path: Path) -> bool:
    """Check if a path is within a virtual environment directory.

    Walks up the directory tree looking for venv markers.

    Args:
        path: Path to check (file or directory).

    Returns:
        True if the path is within a virtual environment.
    """
    current = path.parent if path.is_file() else path
    while current != current.parent:
        if is_venv_directory(current):
            return True
        current = current.parent
    return False
