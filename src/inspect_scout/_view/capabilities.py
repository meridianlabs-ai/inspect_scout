from __future__ import annotations

import os
import posixpath
import re
import urllib.parse
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Iterable, Literal

from fastapi import HTTPException
from fsspec.core import split_protocol  # type: ignore
from upath import UPath

from inspect_scout._project.types import ProjectConfig
from inspect_scout._scanjob_config import ScanJobConfig
from inspect_scout._scanspec import ScannerSpec
from inspect_scout._util.constants import DEFAULT_SCANS_DIR
from inspect_scout._view.types import ViewConfig

CapabilityKind = Literal["directory", "file"]
_WINDOWS_DRIVE_PATH = re.compile(r"^[A-Za-z]:[\\/]")


@dataclass(frozen=True)
class _RemotePath:
    scheme: str
    authority: str
    path: PurePosixPath
    query: str


@dataclass(frozen=True)
class PathCapability:
    kind: CapabilityKind
    _local: Path | None
    _remote: _RemotePath | None

    @classmethod
    def parse(cls, kind: CapabilityKind, location: str) -> "PathCapability":
        local = _canonical_local_path(location)
        remote = None if local is not None else _canonical_remote_path(location)
        if local is None and remote is None:
            raise ValueError(f"Invalid Scout capability path: {location}")
        if kind == "directory" and remote:
            if remote.scheme in ("http", "https"):
                raise ValueError(f"Unsupported Scout directory scheme: {remote.scheme}")
            if remote.query:
                raise ValueError("Scout directory capabilities cannot contain a query")
        return cls(kind=kind, _local=local, _remote=remote)

    def allows(self, location: str) -> bool:
        if self._local is not None:
            candidate = _canonical_local_path(location)
            if candidate is None:
                return False
            if self.kind == "file":
                return candidate == self._local
            return candidate.is_relative_to(self._local)

        remote_candidate = _canonical_remote_path(location)
        if remote_candidate is None or self._remote is None:
            return False
        if (
            remote_candidate.scheme != self._remote.scheme
            or remote_candidate.authority != self._remote.authority
        ):
            return False
        if self.kind == "file":
            return (
                remote_candidate.path == self._remote.path
                and remote_candidate.query == self._remote.query
            )
        if remote_candidate.query:
            return False
        return remote_candidate.path.is_relative_to(self._remote.path)


@dataclass(frozen=True)
class ViewerCapabilities:
    """Maximum path and execution capabilities granted at viewer startup."""

    project: PathCapability
    transcripts: tuple[PathCapability, ...]
    scans: tuple[PathCapability, ...]
    files: tuple[PathCapability, ...]

    @classmethod
    def from_view_config(
        cls,
        view_config: ViewConfig,
        project_dir: Path,
    ) -> "ViewerCapabilities":
        project = PathCapability.parse("directory", str(project_dir.resolve()))
        transcript_location = (
            view_config.transcripts_cli or view_config.project.transcripts
        )
        scans_location = (
            view_config.scans_cli or view_config.project.scans or DEFAULT_SCANS_DIR
        )
        transcripts = (
            (PathCapability.parse("directory", transcript_location),)
            if transcript_location
            else ()
        )
        scans = (PathCapability.parse("directory", scans_location),)
        files = tuple(
            PathCapability.parse("file", location)
            for location in _configured_files(view_config.project)
            if not project.allows(location)
        )
        return cls(
            project=project,
            transcripts=transcripts,
            scans=scans,
            files=files,
        )

    def require_transcripts(self, location: str) -> str:
        return self._require_directory(self.transcripts, location, "transcripts")

    def require_scans(self, location: str) -> str:
        return self._require_directory(self.scans, location, "scans")

    def allows_scans(self, location: str) -> bool:
        return any(capability.allows(location) for capability in self.scans)

    def resolve_scan(self, scans_root: str, child: str) -> UPath:
        root = self.require_scans(scans_root)
        if _is_absolute_or_traversing(child):
            raise _forbidden("Scan path must be relative to the configured scans root")
        candidate = str(UPath(root) / child)
        self.require_scans(candidate)
        return UPath(candidate)

    def validate_project_update(self, config: ProjectConfig) -> None:
        self.validate_scan_job(config)

    def validate_scan_job(self, config: ScanJobConfig) -> None:
        if config.transcripts is not None:
            self.require_transcripts(config.transcripts)
        if config.scans is not None:
            self.require_scans(config.scans)
        if isinstance(config.model_args, str):
            self.require_file(config.model_args, "model arguments")
        for scanner in _scanner_specs(config.scanners):
            if scanner.file is not None:
                self.require_file(scanner.file, "scanner")
        if config.validation:
            for validation in config.validation.values():
                if isinstance(validation, str):
                    self.require_file(validation, "validation")

    def require_file(self, location: str, label: str) -> str:
        if self.project.allows(location) or any(
            capability.allows(location) for capability in self.files
        ):
            return location
        raise _forbidden(
            f"{label.capitalize()} file is outside the viewer's startup capabilities"
        )

    def _require_directory(
        self,
        capabilities: tuple[PathCapability, ...],
        location: str,
        label: str,
    ) -> str:
        if any(capability.allows(location) for capability in capabilities):
            return location
        raise _forbidden(
            f"Requested {label} location is outside the viewer's startup capabilities"
        )


def _configured_files(config: ProjectConfig) -> set[str]:
    files: set[str] = set()
    if isinstance(config.model_args, str):
        files.add(config.model_args)
    for scanner in _scanner_specs(config.scanners):
        if scanner.file:
            files.add(scanner.file)
    if config.validation:
        files.update(
            value for value in config.validation.values() if isinstance(value, str)
        )
    return files


def _scanner_specs(
    scanners: list[ScannerSpec] | dict[str, ScannerSpec] | None,
) -> Iterable[ScannerSpec]:
    if scanners is None:
        return ()
    return scanners.values() if isinstance(scanners, dict) else scanners


def _forbidden(detail: str) -> HTTPException:
    return HTTPException(status_code=403, detail=detail)


def _is_absolute_or_traversing(location: str) -> bool:
    protocol, _ = split_protocol(location)
    if protocol is not None:
        return True
    if Path(location).is_absolute() or _WINDOWS_DRIVE_PATH.match(location):
        return True
    decoded = urllib.parse.unquote(location)
    decoded_protocol, _ = split_protocol(decoded)
    return (
        decoded_protocol is not None
        or PurePosixPath(decoded).is_absolute()
        or bool(_WINDOWS_DRIVE_PATH.match(decoded))
        or "\\" in decoded
        or ".." in PurePosixPath(decoded).parts
    )


def _canonical_local_path(location: str) -> Path | None:
    if not location:
        return None
    if os.name == "nt" and _WINDOWS_DRIVE_PATH.match(location):
        protocol = None
    else:
        protocol, _ = split_protocol(location)
    if protocol is None:
        path = location
    elif protocol.lower() == "file":
        file_path = _local_path_from_file_uri(location)
        if file_path is None:
            return None
        path = file_path
    else:
        return None
    try:
        return Path(path).resolve()
    except (OSError, RuntimeError, ValueError):
        return None


def _local_path_from_file_uri(
    location: str,
    *,
    windows: bool | None = None,
) -> str | None:
    windows = os.name == "nt" if windows is None else windows
    try:
        parsed = urllib.parse.urlsplit(location)
        port = parsed.port
    except ValueError:
        return None
    if (
        parsed.query
        or parsed.fragment
        or parsed.username is not None
        or parsed.password is not None
        or port is not None
    ):
        return None

    decoded_path = urllib.parse.unquote(parsed.path)
    if "\\" in decoded_path:
        return None

    authority = parsed.hostname or ""
    if authority and authority.lower() != "localhost":
        if not windows or not decoded_path.startswith("/"):
            return None
        if len(PurePosixPath(decoded_path).parts) < 2:
            return None
        return str(PureWindowsPath(f"//{authority}{decoded_path}"))

    if (
        windows
        and decoded_path.startswith("/")
        and len(decoded_path) > 3
        and decoded_path[2] == ":"
    ):
        return decoded_path[1:]
    return decoded_path


def _canonical_remote_path(location: str) -> _RemotePath | None:
    protocol, _ = split_protocol(location)
    if protocol is None or protocol.lower() == "file":
        return None
    try:
        parsed = urllib.parse.urlsplit(location)
    except ValueError:
        return None
    if (
        not parsed.netloc
        or parsed.fragment
        or parsed.username is not None
        or parsed.password is not None
        or "\\" in parsed.path
    ):
        return None
    decoded_path = urllib.parse.unquote(parsed.path)
    if "\\" in decoded_path or ".." in PurePosixPath(decoded_path).parts:
        return None
    path = posixpath.normpath("/" + decoded_path.lstrip("/"))
    return _RemotePath(
        scheme=protocol.lower(),
        authority=parsed.netloc.lower(),
        path=PurePosixPath(path),
        query=parsed.query,
    )
