"""GitHub LFS batch API client.

Downloads LFS objects from public GitHub repositories using the
batch API endpoint. No authentication is required for public repos.
"""

import hashlib
import json
import logging
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from .exceptions import LFSBatchError, LFSDownloadError

logger = logging.getLogger(__name__)

_LFS_MEDIA_TYPE = "application/vnd.git-lfs+json"

# Default repo URL — can be overridden for testing.
DEFAULT_REPO_URL = "https://github.com/meridianlabs-ai/inspect_scout.git"


@dataclass(frozen=True)
class LFSDownloadInfo:
    """Download URL and metadata for a single LFS object."""

    oid: str
    size: int
    href: str


def fetch_download_urls(
    objects: list[tuple[str, int]],
    repo_url: str = DEFAULT_REPO_URL,
) -> list[LFSDownloadInfo]:
    """Get download URLs for LFS objects via the batch API.

    Args:
        objects: List of (oid, size) tuples to request.
        repo_url: HTTPS URL of the git repository.

    Returns:
        List of download info for each object that has a download URL.

    Raises:
        LFSBatchError: If the batch API call fails.
    """
    if not objects:
        return []

    batch_endpoint = f"{repo_url}/info/lfs/objects/batch"
    payload = {
        "operation": "download",
        "transfers": ["basic"],
        "objects": [{"oid": oid, "size": size} for oid, size in objects],
    }

    req = urllib.request.Request(
        batch_endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": _LFS_MEDIA_TYPE,
            "Accept": _LFS_MEDIA_TYPE,
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise LFSBatchError(f"LFS batch API returned HTTP {e.code}: {e.reason}") from e
    except (urllib.error.URLError, OSError) as e:
        raise LFSBatchError(f"Failed to reach LFS batch API: {e}") from e
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise LFSBatchError(f"Failed to parse LFS batch API response: {e}") from e

    results: list[LFSDownloadInfo] = []
    for obj in body.get("objects", []):
        oid = obj.get("oid", "")
        size = obj.get("size", 0)
        actions = obj.get("actions", {})
        download = actions.get("download", {})
        href = download.get("href", "")

        if obj.get("error"):
            err = obj["error"]
            logger.warning(
                "LFS object %s: server error %s — %s",
                oid[:12],
                err.get("code", "?"),
                err.get("message", "unknown"),
            )
            continue

        if not href:
            logger.warning("LFS object %s: no download URL in response", oid[:12])
            continue

        results.append(LFSDownloadInfo(oid=oid, size=size, href=href))

    return results


def download_lfs_object(
    info: LFSDownloadInfo,
    dest_path: Path,
) -> None:
    """Download a single LFS object and verify its integrity.

    Args:
        info: Download info from the batch API.
        dest_path: Where to write the downloaded file.

    Raises:
        LFSDownloadError: If download fails or integrity check fails.
    """
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    req = urllib.request.Request(info.href, method="GET")

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            hasher = hashlib.sha256()
            total_bytes = 0

            with open(dest_path, "wb") as f:
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    f.write(chunk)
                    hasher.update(chunk)
                    total_bytes += len(chunk)
    except (urllib.error.URLError, OSError) as e:
        dest_path.unlink(missing_ok=True)
        raise LFSDownloadError(
            f"Failed to download LFS object {info.oid[:12]}: {e}"
        ) from e

    actual_oid = hasher.hexdigest()
    if actual_oid != info.oid:
        dest_path.unlink(missing_ok=True)
        raise LFSDownloadError(
            f"SHA-256 mismatch for LFS object {info.oid[:12]}: "
            f"expected {info.oid}, got {actual_oid}"
        )

    if total_bytes != info.size:
        logger.warning(
            "LFS object %s: expected %d bytes, got %d",
            info.oid[:12],
            info.size,
            total_bytes,
        )
