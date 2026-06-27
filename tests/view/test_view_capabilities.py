from __future__ import annotations

import base64
import io
import zipfile
from contextlib import contextmanager
from pathlib import Path, PureWindowsPath
from typing import Iterator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from inspect_scout._project._project import read_project_config_with_etag
from inspect_scout._project.types import ProjectConfig
from inspect_scout._scanjob_config import ScanJobConfig
from inspect_scout._scanspec import ScannerSpec
from inspect_scout._view._api_v2 import v2_api_app
from inspect_scout._view.capabilities import (
    PathCapability,
    ViewerCapabilities,
    _local_path_from_file_uri,
)
from inspect_scout._view.types import ViewConfig
from starlette.exceptions import HTTPException


def _encode(value: str) -> str:
    return base64.urlsafe_b64encode(value.encode()).decode().rstrip("=")


def _capabilities(
    project_dir: Path,
    transcripts: str,
    scans: str,
    *,
    project: ProjectConfig | None = None,
) -> ViewerCapabilities:
    return ViewerCapabilities.from_view_config(
        ViewConfig(
            project=project or ProjectConfig(transcripts=transcripts, scans=scans)
        ),
        project_dir,
    )


def test_local_and_remote_path_capabilities(tmp_path: Path) -> None:
    local = tmp_path / "logs"
    sibling = tmp_path / "logs-archive"
    local.mkdir()
    sibling.mkdir()
    local_scope = PathCapability.parse("directory", str(local))
    assert local_scope.allows(str(local / "run.eval"))
    assert not local_scope.allows(str(sibling / "run.eval"))

    remote_scope = PathCapability.parse("directory", "s3://bucket/logs")
    assert remote_scope.allows("s3://bucket/logs/run.eval")
    assert not remote_scope.allows("s3://bucket/logs-archive/run.eval")
    assert not remote_scope.allows("s3://other/logs/run.eval")
    assert not remote_scope.allows("s3://bucket/logs/%2e%2e/private")

    remote_file = PathCapability.parse("file", "memory://bucket/logs/secret")
    assert (
        remote_file.resolve("memory://bucket/logs//secret")
        == "memory://bucket/logs/secret"
    )


def test_local_capability_retains_selected_symlink_target(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    selected = tmp_path / "selected"
    first.mkdir()
    second.mkdir()
    (second / "secret.txt").write_text("secret", encoding="utf-8")
    try:
        selected.symlink_to(first, target_is_directory=True)
    except OSError:
        pytest.skip("Creating directory symlinks is not supported")

    capability = PathCapability.parse("directory", str(selected))
    selected.unlink()
    selected.symlink_to(second, target_is_directory=True)

    assert not capability.allows(str(selected / "secret.txt"))


def test_remote_capabilities_preserve_exact_queries() -> None:
    selected = "https://example.test/scanner.py?expires=60&signature=selected"
    capability = PathCapability.parse("file", selected)
    assert capability.allows(selected)
    assert not capability.allows(
        "https://example.test/scanner.py?expires=60&signature=other"
    )
    assert not capability.allows("https://example.test/scanner.py")

    canonical = PathCapability.parse(
        "file",
        "s3://bucket/scanner.py?credential=team%2Fmember&label=hello%20world",
    )
    assert (
        canonical.resolve(
            "s3://bucket/scanner.py?credential=team/member&label=hello world"
        )
        == "s3://bucket/scanner.py?credential=team%2Fmember&label=hello%20world"
    )

    opaque = "https://example.test/scanner.py?token=a%26b&credential=team%2Fmember"
    opaque_capability = PathCapability.parse("file", opaque)
    assert opaque_capability.resolve(opaque) == opaque
    assert (
        opaque_capability.resolve(
            "https://example.test/scanner.py?token=a&b&credential=team%2Fmember"
        )
        is None
    )
    encoded_path = "https://example.test/a%3Fb%23c.py"
    assert (
        PathCapability.parse("file", encoded_path).resolve(encoded_path) == encoded_path
    )

    directory = PathCapability.parse("directory", "s3://bucket/scans")
    assert not directory.allows("s3://bucket/scans/run?version=selected")
    with pytest.raises(ValueError, match="cannot contain a query"):
        PathCapability.parse("directory", "s3://bucket/scans?version=selected")


def test_scan_job_paths_are_replaced_with_resolved_locations(tmp_path: Path) -> None:
    selected_file = "memory://bucket/config/selected.json"
    capabilities = ViewerCapabilities(
        project=PathCapability.parse("directory", str(tmp_path)),
        transcripts=(PathCapability.parse("directory", "memory://bucket/transcripts"),),
        scans=(PathCapability.parse("directory", "memory://bucket/scans"),),
        files=(PathCapability.parse("file", selected_file),),
    )

    resolved = capabilities.resolve_scan_job(
        ScanJobConfig(
            transcripts="memory://bucket/transcripts//team",
            scans="memory://bucket/scans//team",
            model_args="memory://bucket/config//selected.json",
            scanners=[
                ScannerSpec(
                    name="scanner",
                    file="memory://bucket/config//selected.json",
                )
            ],
            validation={"scanner": "memory://bucket/config//selected.json"},
        )
    )

    assert resolved.transcripts == "memory://bucket/transcripts/team"
    assert resolved.scans == "memory://bucket/scans/team"
    assert resolved.model_args == selected_file
    assert isinstance(resolved.scanners, list)
    assert resolved.scanners[0].file == selected_file
    assert resolved.validation == {"scanner": selected_file}


def test_file_uri_parsing_supports_windows_unc_paths() -> None:
    assert _local_path_from_file_uri(
        "file://server/share/scans/run", windows=True
    ) == str(PureWindowsPath("//server/share/scans/run"))
    assert (
        _local_path_from_file_uri("file://server/share/scans/run", windows=False)
        is None
    )


def test_capabilities_resolve_relative_scan_children(tmp_path: Path) -> None:
    scans = tmp_path / "scans"
    transcripts = tmp_path / "transcripts"
    scans.mkdir()
    transcripts.mkdir()
    capabilities = _capabilities(tmp_path, str(transcripts), str(scans))

    resolved = capabilities.resolve_scan(str(scans), "scan_id=abc")
    assert resolved == scans / "scan_id=abc"

    for child in (
        ".",
        str(tmp_path / "outside"),
        "../outside",
        "%2Fetc",
        "s3://bucket/scan",
        "%73%33://bucket/scan",
    ):
        with pytest.raises(HTTPException):
            capabilities.resolve_scan(str(scans), child)


def test_delete_scan_requires_strict_valid_scan_child(tmp_path: Path) -> None:
    transcripts = tmp_path / "transcripts"
    scans = tmp_path / "scans"
    unrelated = scans / "unrelated"
    scan = scans / "scan_id=test"
    transcripts.mkdir()
    unrelated.mkdir(parents=True)
    scan.mkdir()
    (scan / "_scan.json").write_text("{}", encoding="utf-8")
    capabilities = _capabilities(tmp_path, str(transcripts), str(scans))
    store = MagicMock()
    store.read_all.return_value = {}
    recorder = MagicMock()
    status = MagicMock()
    status.spec.scan_id = "test"

    async def read_status(location: str) -> MagicMock:
        if location == str(scan):
            return status
        raise FileNotFoundError

    recorder.status = AsyncMock(side_effect=read_status)

    @contextmanager
    def fake_store() -> Iterator[MagicMock]:
        yield store

    with (
        patch(
            "inspect_scout._view._api_v2_scans.active_scans_store",
            fake_store,
        ),
        patch("inspect_scout._view._api_v2_scans.send2trash") as trash,
        patch(
            "inspect_scout._view._api_v2_scans.scan_recorder_for_location",
            return_value=recorder,
        ),
        TestClient(v2_api_app(capabilities=capabilities)) as client,
    ):
        root_response = client.delete(f"/scans/{_encode(str(scans))}/{_encode('.')}")
        unrelated_response = client.delete(
            f"/scans/{_encode(str(scans))}/{_encode('unrelated')}"
        )
        scan_response = client.delete(
            f"/scans/{_encode(str(scans))}/{_encode('scan_id=test')}"
        )

    assert root_response.status_code == 403
    assert unrelated_response.status_code == 404
    assert scan_response.status_code == 204
    trash.assert_called_once_with(str(scan))


def test_delete_scan_rejects_forged_validation_marker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    transcripts = tmp_path / "transcripts"
    scans = tmp_path / "scans"
    victim = scans / "important-data"
    transcripts.mkdir()
    victim.mkdir(parents=True)
    (victim / "keep.txt").write_text("keep", encoding="utf-8")
    capabilities = _capabilities(tmp_path, str(transcripts), str(scans))
    monkeypatch.chdir(tmp_path)

    with (
        patch("inspect_scout._view._api_v2_scans.send2trash") as trash,
        TestClient(v2_api_app(capabilities=capabilities)) as client,
    ):
        create_response = client.post(
            "/validations",
            json={
                "path": (victim / "_scan.json").as_uri(),
                "cases": [{"id": "x", "target": True}],
            },
        )
        delete_response = client.delete(
            f"/scans/{_encode(str(scans))}/{_encode('important-data')}"
        )

    assert create_response.status_code == 200
    assert delete_response.status_code == 404
    trash.assert_not_called()


def test_delete_scan_blocks_active_scan_path_alias(tmp_path: Path) -> None:
    transcripts = tmp_path / "transcripts"
    scans = tmp_path / "scans"
    scan = scans / "scan_id=test"
    transcripts.mkdir()
    scan.mkdir(parents=True)
    capabilities = _capabilities(tmp_path, str(transcripts), str(scans))
    status = MagicMock()
    status.spec.scan_id = "test"
    recorder = MagicMock()
    recorder.status = AsyncMock(return_value=status)
    store = MagicMock()
    store.read_all.return_value = {
        "test": MagicMock(scan_id="test", location="scans/scan_id=test")
    }

    @contextmanager
    def fake_store() -> Iterator[MagicMock]:
        yield store

    with (
        patch(
            "inspect_scout._view._api_v2_scans.active_scans_store",
            fake_store,
        ),
        patch(
            "inspect_scout._view._api_v2_scans.scan_recorder_for_location",
            return_value=recorder,
        ),
        patch("inspect_scout._view._api_v2_scans.send2trash") as trash,
        TestClient(v2_api_app(capabilities=capabilities)) as client,
    ):
        response = client.delete(
            f"/scans/{_encode(str(scans))}/{_encode('scan_id=test')}"
        )

    assert response.status_code == 409
    trash.assert_not_called()


def test_project_updates_may_narrow_but_not_expand_capabilities(
    tmp_path: Path,
) -> None:
    transcripts = tmp_path / "transcripts"
    scans = tmp_path / "scans"
    transcripts.mkdir()
    scans.mkdir()
    capabilities = _capabilities(tmp_path, str(transcripts), str(scans))

    capabilities.validate_project_update(
        ProjectConfig(
            transcripts=str(transcripts / "subset"),
            scans=str(scans / "team"),
        )
    )

    with pytest.raises(HTTPException, match="outside"):
        capabilities.validate_project_update(
            ProjectConfig(
                transcripts=str(tmp_path / "other-transcripts"),
                scans=str(scans),
            )
        )


def test_scan_job_files_are_limited_to_project_or_startup_files(
    tmp_path: Path,
) -> None:
    transcripts = tmp_path / "transcripts"
    scans = tmp_path / "scans"
    outside = tmp_path.parent / "outside-scanner.py"
    transcripts.mkdir()
    scans.mkdir()
    project_scanner = tmp_path / "scanner.py"
    capabilities = _capabilities(tmp_path, str(transcripts), str(scans))

    capabilities.validate_scan_job(
        ScanJobConfig(scanners=[ScannerSpec(name="scanner", file=str(project_scanner))])
    )
    with pytest.raises(HTTPException, match="Scanner file"):
        capabilities.validate_scan_job(
            ScanJobConfig(scanners=[ScannerSpec(name="scanner", file=str(outside))])
        )


def test_scans_api_rejects_out_of_scope_roots_and_absolute_children(
    tmp_path: Path,
) -> None:
    transcripts = tmp_path / "transcripts"
    scans = tmp_path / "scans"
    outside = tmp_path / "outside"
    transcripts.mkdir()
    scans.mkdir()
    outside.mkdir()
    capabilities = _capabilities(tmp_path, str(transcripts), str(scans))

    with TestClient(v2_api_app(capabilities=capabilities)) as client:
        outside_root = client.post(f"/scans/{_encode(str(outside))}", json={})
        absolute_child = client.get(
            f"/scans/{_encode(str(scans))}/{_encode(str(outside))}",
            headers={"Accept": "application/zip"},
        )

    assert outside_root.status_code == 403
    assert absolute_child.status_code == 403


def test_scan_zip_rejects_symlinked_files_outside_scan(
    tmp_path: Path,
) -> None:
    transcripts = tmp_path / "transcripts"
    scans = tmp_path / "scans"
    scan = scans / "scan_id=test"
    outside = tmp_path / "secret.txt"
    transcripts.mkdir()
    scan.mkdir(parents=True)
    outside.write_text("secret", encoding="utf-8")
    symlink = scan / "result.txt"
    try:
        symlink.symlink_to(outside)
    except OSError:
        pytest.skip("Creating file symlinks is not supported")
    capabilities = _capabilities(tmp_path, str(transcripts), str(scans))

    with TestClient(v2_api_app(capabilities=capabilities)) as client:
        response = client.get(
            f"/scans/{_encode(str(scans))}/{_encode('scan_id=test')}",
            headers={"Accept": "application/zip"},
        )

    assert response.status_code == 403
    assert response.content != outside.read_bytes()
    with pytest.raises(zipfile.BadZipFile):
        zipfile.ZipFile(io.BytesIO(response.content))


def test_transcript_and_search_routes_reject_out_of_scope_roots(
    tmp_path: Path,
) -> None:
    transcripts = tmp_path / "transcripts"
    scans = tmp_path / "scans"
    outside = tmp_path / "outside"
    transcripts.mkdir()
    scans.mkdir()
    outside.mkdir()
    capabilities = _capabilities(tmp_path, str(transcripts), str(scans))

    with TestClient(v2_api_app(capabilities=capabilities)) as client:
        listing = client.post(f"/transcripts/{_encode(str(outside))}", json={})
        search = client.post(
            f"/transcripts/{_encode(str(outside))}/id/search",
            json={"type": "grep", "query": "test"},
        )

    assert listing.status_code == 403
    assert search.status_code == 403


def test_active_scans_hide_out_of_scope_locations(tmp_path: Path) -> None:
    transcripts = tmp_path / "transcripts"
    scans = tmp_path / "scans"
    transcripts.mkdir()
    scans.mkdir()
    capabilities = _capabilities(tmp_path, str(transcripts), str(scans))
    store = MagicMock()
    store.read_all.return_value = {
        "outside": MagicMock(location=str(tmp_path / "outside"))
    }

    @contextmanager
    def fake_store() -> Iterator[MagicMock]:
        yield store

    with (
        patch(
            "inspect_scout._view._api_v2_scans.active_scans_store",
            fake_store,
        ),
        TestClient(v2_api_app(capabilities=capabilities)) as client,
    ):
        response = client.get("/scans/active")

    assert response.status_code == 200
    assert response.json()["items"] == {}


def test_start_scan_rejects_path_expansion_before_spawning(
    tmp_path: Path,
) -> None:
    transcripts = tmp_path / "transcripts"
    scans = tmp_path / "scans"
    outside = tmp_path / "outside"
    transcripts.mkdir()
    scans.mkdir()
    capabilities = _capabilities(tmp_path, str(transcripts), str(scans))

    with (
        patch("inspect_scout._view._api_v2_scans._spawn_scan_subprocess") as spawn,
        TestClient(v2_api_app(capabilities=capabilities)) as client,
    ):
        response = client.post(
            "/startscan",
            json={
                "transcripts": str(outside),
                "scanners": [{"name": "inspect_scout/llm_scanner"}],
            },
        )

    assert response.status_code == 403
    spawn.assert_not_called()


def test_start_scan_revalidates_project_config_before_spawning(
    tmp_path: Path,
) -> None:
    transcripts = tmp_path / "transcripts"
    scans = tmp_path / "scans"
    transcripts.mkdir()
    scans.mkdir()
    capabilities = _capabilities(tmp_path, str(transcripts), str(scans))
    expanded_project = ProjectConfig(
        transcripts=str(tmp_path / "outside"),
        scans=str(scans),
    )

    with (
        patch(
            "inspect_scout._view._api_v2_scans.read_project",
            return_value=expanded_project,
        ),
        patch("inspect_scout._view._api_v2_scans._spawn_scan_subprocess") as spawn,
        TestClient(v2_api_app(capabilities=capabilities)) as client,
    ):
        response = client.post(
            "/startscan",
            json={
                "scanners": [{"name": "inspect_scout/llm_scanner"}],
            },
        )

    assert response.status_code == 403
    spawn.assert_not_called()


def test_start_scan_rejects_child_reported_location_outside_capabilities(
    tmp_path: Path,
) -> None:
    transcripts = tmp_path / "transcripts"
    scans = tmp_path / "scans"
    outside = tmp_path / "outside"
    transcripts.mkdir()
    scans.mkdir()
    capabilities = _capabilities(tmp_path, str(transcripts), str(scans))
    proc = MagicMock(pid=123)
    active_info = MagicMock(scan_id="test", location=str(outside))

    with (
        patch(
            "inspect_scout._view._api_v2_scans.read_project",
            return_value=ProjectConfig(
                transcripts=str(transcripts),
                scans=str(scans),
            ),
        ),
        patch(
            "inspect_scout._view._api_v2_scans._spawn_scan_subprocess",
            return_value=(proc, str(tmp_path / "missing.json"), [], []),
        ),
        patch(
            "inspect_scout._view._api_v2_scans._wait_for_active_scan",
            new=AsyncMock(return_value=active_info),
        ),
        patch(
            "inspect_scout._view._api_v2_scans.scan_recorder_for_location"
        ) as recorder,
        TestClient(v2_api_app(capabilities=capabilities)) as client,
    ):
        response = client.post(
            "/startscan",
            json={
                "scanners": [{"name": "inspect_scout/llm_scanner"}],
            },
        )

    assert response.status_code == 403
    recorder.assert_not_called()


def test_project_api_rejects_capability_expansion(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transcripts = tmp_path / "transcripts"
    scans = tmp_path / "scans"
    transcripts.mkdir()
    scans.mkdir()
    capabilities = _capabilities(tmp_path, str(transcripts), str(scans))
    monkeypatch.chdir(tmp_path)

    with TestClient(v2_api_app(capabilities=capabilities)) as client:
        response = client.put(
            "/project/config",
            json={
                "transcripts": str(tmp_path / "outside"),
                "scans": str(scans),
            },
        )

    assert response.status_code == 403
    assert not (tmp_path / "scout.yaml").exists()


def test_project_api_preserves_relative_path_spelling(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transcripts = tmp_path / "transcripts"
    scans = tmp_path / "scans"
    transcripts.mkdir()
    scans.mkdir()
    capabilities = _capabilities(tmp_path, str(transcripts), str(scans))
    monkeypatch.chdir(tmp_path)

    with TestClient(v2_api_app(capabilities=capabilities)) as client:
        response = client.put(
            "/project/config",
            json={
                "transcripts": "./transcripts",
                "scans": "./scans",
            },
        )

    saved, _etag = read_project_config_with_etag()
    assert response.status_code == 200
    assert saved.transcripts == "./transcripts"
    assert saved.scans == "./scans"
