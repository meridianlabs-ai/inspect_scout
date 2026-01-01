"""Code formatter detection and application.

Detects if a project has ruff configured and applies formatting to generated code.
"""

import shutil
import subprocess
from pathlib import Path


def format_with_ruff(source: str, project_dir: Path | None = None) -> str:
    """Format source code with ruff if available and configured.

    Only formats if the project has explicitly opted into ruff by having
    a ruff.toml, .ruff.toml, or pyproject.toml with [tool.ruff] section.

    Args:
        source: Python source code to format.
        project_dir: Project directory for config detection (optional).
            If not provided or no ruff config found, returns source unchanged.

    Returns:
        Formatted source if ruff is available and project has ruff config,
        otherwise returns original source unchanged.
    """
    # Check if ruff is available
    if not is_ruff_available():
        return source

    # Only format if project has opted into ruff
    if project_dir is None or not detect_ruff_config(project_dir):
        return source

    try:
        # Build command
        cmd = ["ruff", "format", "--stdin-filename=scanner.py", "-"]

        # Run ruff format with source as stdin
        result = subprocess.run(
            cmd,
            input=source,
            capture_output=True,
            text=True,
            cwd=project_dir,
            timeout=30,
        )

        if result.returncode == 0:
            return result.stdout
        else:
            # On error, return original source
            return source

    except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError):
        # On any error, return original source
        return source


def detect_ruff_config(project_dir: Path) -> bool:
    """Check if project has ruff configuration.

    Looks for:
    - ruff.toml
    - .ruff.toml
    - pyproject.toml with [tool.ruff] section

    Args:
        project_dir: Project directory to check for ruff config.

    Returns:
        True if ruff configuration is found, False otherwise.
    """
    # Check for ruff.toml or .ruff.toml
    if (project_dir / "ruff.toml").exists():
        return True
    if (project_dir / ".ruff.toml").exists():
        return True

    # Check for pyproject.toml with [tool.ruff] section
    pyproject = project_dir / "pyproject.toml"
    if pyproject.exists():
        try:
            content = pyproject.read_text()
            if "[tool.ruff]" in content:
                return True
        except OSError:
            pass

    return False


def is_ruff_available() -> bool:
    """Check if ruff is available in PATH."""
    return shutil.which("ruff") is not None
