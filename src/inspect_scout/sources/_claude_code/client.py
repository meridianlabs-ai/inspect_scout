"""Claude Code file discovery and reading utilities.

Claude Code stores session files in ~/.claude/projects/[encoded-path]/.
Each session is a JSONL file with UUID filename.
Agent sessions are stored as agent-{agentId}.jsonl in the same directory.
"""

from datetime import datetime
from logging import getLogger
from os import PathLike
from pathlib import Path
from typing import Any

logger = getLogger(__name__)

# Claude Code source type constant
CLAUDE_CODE_SOURCE_TYPE = "claude_code"

# Default Claude Code projects directory
DEFAULT_CLAUDE_DIR = Path.home() / ".claude" / "projects"


def decode_project_path(encoded: str, validate: bool = True) -> str:
    """Decode a Claude Code project path encoding.

    Claude Code encodes paths by replacing / with -.
    E.g., "-Users-jjallaire-dev-project" -> "/Users/jjallaire/dev/project"

    The encoding is lossy when directory names contain hyphens. When validate=True,
    this function tries different interpretations and returns the first one that
    exists on the filesystem. For example, "-Users-my-project-foo" could decode to:
    - /Users/my-project/foo (if /Users/my-project exists)
    - /Users/my/project-foo (if /Users/my/project-foo exists)

    Args:
        encoded: The encoded project path (directory name)
        validate: If True, validate against filesystem to handle hyphenated dirs.
            If False, use naive replacement (faster but may be wrong).

    Returns:
        The decoded file system path (best guess if validation fails)
    """
    if not encoded.startswith("-"):
        return encoded

    # Remove leading dash and split on remaining dashes
    parts = encoded[1:].split("-")

    if not validate:
        # Fast path: naive replacement
        return "/" + "/".join(parts)

    # Try to find a valid path by testing different split points
    decoded = _find_valid_path(parts)
    if decoded:
        return decoded

    # Fallback: naive replacement if no valid path found
    return "/" + "/".join(parts)


def _find_valid_path(parts: list[str]) -> str | None:
    """Find a valid filesystem path by testing different hyphen interpretations.

    First tries the simple interpretation (all hyphens are path separators).
    If that doesn't exist, uses DFS to try different combinations where some
    hyphens are literal characters in directory names.

    Args:
        parts: List of path components split on hyphens

    Returns:
        A valid path if found, None otherwise
    """
    if not parts:
        return None

    # Fast path: try naive interpretation first (most common case)
    naive_path = "/" + "/".join(parts)
    if Path(naive_path).exists():
        return naive_path

    # Slow path: DFS to find valid path when directories contain hyphens
    def search(index: int, current_path: Path, current_str: str) -> str | None:
        """Recursively search for valid paths."""
        if index >= len(parts):
            if current_path.exists():
                return current_str
            return None

        part = parts[index]

        # Option 1: Add as new path component (use /)
        new_path_slash = current_path / part
        new_str_slash = current_str + "/" + part
        # Continue if path exists OR we're not at the last segment
        # (we need to explore full paths before determining validity)
        if new_path_slash.exists() or index < len(parts) - 1:
            result = search(index + 1, new_path_slash, new_str_slash)
            if result:
                return result

        # Option 2: Merge with previous component using hyphen
        # Only if we have a previous component to merge with
        if current_str:
            parent_path = current_path.parent
            last_component = current_path.name
            merged_component = last_component + "-" + part
            new_path_hyphen = parent_path / merged_component
            # Reconstruct string: replace last component with merged one
            last_slash = current_str.rfind("/")
            new_str_hyphen = current_str[:last_slash] + "/" + merged_component

            if new_path_hyphen.exists() or index < len(parts) - 1:
                result = search(index + 1, new_path_hyphen, new_str_hyphen)
                if result:
                    return result

        return None

    # Start search from root
    return search(0, Path("/"), "")


def encode_project_path(path: str) -> str:
    """Encode a file system path for Claude Code directory naming.

    Args:
        path: The file system path

    Returns:
        The encoded directory name
    """
    return path.replace("/", "-")


def discover_session_files(
    path: str | PathLike[str] | None = None,
    session_id: str | None = None,
    from_time: datetime | None = None,
    to_time: datetime | None = None,
) -> list[Path]:
    """Discover Claude Code session files.

    Args:
        path: Path to search. Can be:
            - None: Scan all projects in ~/.claude/projects/
            - A project directory (e.g., ~/.claude/projects/-Users-foo-bar/)
            - A specific .jsonl file
        session_id: If provided, only return files matching this session UUID
        from_time: Only return files modified on or after this time
        to_time: Only return files modified before this time

    Returns:
        List of session file paths, sorted by modification time (newest first)
    """
    session_files: list[Path] = []

    if path is None:
        # Scan all projects
        if not DEFAULT_CLAUDE_DIR.exists():
            logger.warning(f"Claude Code directory not found: {DEFAULT_CLAUDE_DIR}")
            return []

        for project_dir in DEFAULT_CLAUDE_DIR.iterdir():
            if project_dir.is_dir():
                session_files.extend(
                    _find_sessions_in_directory(project_dir, session_id)
                )
    else:
        search_path = Path(path)

        if not search_path.exists():
            logger.warning(f"Path does not exist: {search_path}")
            return []

        if search_path.is_file():
            # Specific file
            if search_path.suffix == ".jsonl":
                session_files.append(search_path)
        elif search_path.is_dir():
            # Project directory or parent directory
            if any(search_path.glob("*.jsonl")):
                # It's a project directory with session files
                session_files.extend(
                    _find_sessions_in_directory(search_path, session_id)
                )
            else:
                # It might be a parent containing project directories
                for project_dir in search_path.iterdir():
                    if project_dir.is_dir():
                        session_files.extend(
                            _find_sessions_in_directory(project_dir, session_id)
                        )

    # Filter by session_id if specified and not already filtered
    if session_id:
        session_files = [f for f in session_files if f.stem == session_id]

    # Filter by time range
    if from_time or to_time:
        filtered = []
        for f in session_files:
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            if from_time and mtime < from_time:
                continue
            if to_time and mtime >= to_time:
                continue
            filtered.append(f)
        session_files = filtered

    # Sort by modification time (newest first)
    session_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

    return session_files


def _find_sessions_in_directory(
    directory: Path, session_id: str | None = None
) -> list[Path]:
    """Find session files in a project directory.

    Excludes agent-*.jsonl files (those are loaded separately when needed).

    Args:
        directory: The project directory to search
        session_id: Optional specific session to find

    Returns:
        List of main session file paths
    """
    sessions = []

    for jsonl_file in directory.glob("*.jsonl"):
        # Skip agent files - they're loaded separately
        if jsonl_file.name.startswith("agent-"):
            continue

        # If looking for specific session, match by stem (UUID)
        if session_id:
            if jsonl_file.stem == session_id:
                sessions.append(jsonl_file)
        else:
            sessions.append(jsonl_file)

    return sessions


def find_agent_file(project_dir: Path, agent_id: str) -> Path | None:
    """Find an agent session file by ID.

    Args:
        project_dir: The project directory containing session files
        agent_id: The agent ID (e.g., "a038f97")

    Returns:
        Path to agent file, or None if not found
    """
    agent_file = project_dir / f"agent-{agent_id}.jsonl"
    if agent_file.exists():
        return agent_file
    return None


def read_jsonl_events(path: Path) -> list[dict[str, Any]]:
    """Read all events from a JSONL file.

    Args:
        path: Path to the JSONL file

    Returns:
        List of parsed JSON events
    """
    import json

    events = []
    with open(path, encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError as e:
                logger.warning(f"Invalid JSON at {path}:{line_num}: {e}")
                continue
    return events


def get_project_path_from_file(session_file: Path) -> str:
    """Extract the project path from a session file location.

    Args:
        session_file: Path to a session file

    Returns:
        The decoded project path
    """
    # The parent directory name is the encoded project path
    encoded = session_file.parent.name
    return decode_project_path(encoded)


def get_source_uri(session_file: Path, session_id: str | None = None) -> str:
    """Generate a source URI for a session file.

    Args:
        session_file: Path to the session file
        session_id: Optional specific session within the file (for split sessions)

    Returns:
        A file:// URI pointing to the session
    """
    uri = f"file://{session_file}"
    if session_id:
        uri += f"#{session_id}"
    return uri
