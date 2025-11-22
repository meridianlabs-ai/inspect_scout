import re
import subprocess
from logging import getLogger

from inspect_ai._util.git import git_context

from inspect_scout._scanspec import GIT_VERSION_UNKNOWN, ScanRevision

logger = getLogger(__name__)


def scan_revision() -> ScanRevision | None:
    git = git_context()
    if git is not None:
        return ScanRevision(
            type="git",
            origin=git.origin,
            version=git_version_to_semver(),
            commit=git.commit,
        )
    else:
        return None


def get_git_describe() -> str | None:
    """Run git describe and return the output string."""
    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--dirty", "--always", "--long"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as ex:
        logger.warning(f"Error running git describe: {ex}")
        return None


def parse_git_describe_to_semver(describe: str) -> str:
    """Parse git describe output and convert to semver format."""
    # Parse: v0.2.2-539-g4ef4bfd or v0.2.2-539-g4ef4bfd-dirty
    # --long ensures we always get the count even on exact tags
    match = re.match(r"^v?([0-9.]+)-(\d+)-g([0-9a-f]+)(-dirty)?$", describe)

    if not match:
        # Fallback for no tags
        return GIT_VERSION_UNKNOWN

    base_version = match.group(1)  # 0.2.2
    commits = match.group(2)  # 539
    commit_hash = match.group(3)  # 4ef4bfd
    dirty = match.group(4)  # -dirty or None

    if commits == "0":
        # Exactly on a tag
        version = base_version
        if dirty:
            version += "+dirty"
    else:
        # Post-release dev version
        next_version = bump_version(base_version)
        version = f"{next_version}-dev.{commits}+g{commit_hash}"
        if dirty:
            version += ".dirty"

    return version


def git_version_to_semver() -> str:
    """Convert git describe output to semver format"""
    describe = get_git_describe()
    if describe is None:
        return GIT_VERSION_UNKNOWN
    return parse_git_describe_to_semver(describe)


def bump_version(version_str: str) -> str:
    """Bump the patch version: 0.2.2 -> 0.2.3"""
    parts = version_str.split(".")
    if len(parts) >= 3:
        # Standard semver: major.minor.patch
        parts[2] = str(int(parts[2]) + 1)
    elif len(parts) == 2:
        # major.minor -> major.minor.1
        parts.append("1")
    else:
        # major -> major.0.1
        parts.extend(["0", "1"])
    return ".".join(parts)
