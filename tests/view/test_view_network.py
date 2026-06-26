from __future__ import annotations

import base64
import importlib
import inspect
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from httpx import Response
from inspect_scout._view.network import (
    Authority,
    Origin,
    ViewerNetworkPolicy,
    ViewerNetworkPolicyError,
    resolve_viewer_network_policy,
    unsafe_network_warning,
)
from inspect_scout._view.server import standalone_view_app, view_server
from inspect_scout._view.types import ViewConfig
from starlette.types import ASGIApp


def _policy(
    *,
    bind_host: str = "127.0.0.1",
    port: int = 7576,
    trusted_hosts: tuple[str, ...] = (),
    trusted_origins: tuple[str, ...] = (),
    authorization: str | None = None,
    unsafe_allow_unauthenticated: bool = False,
    root_path: str = "",
) -> ViewerNetworkPolicy:
    return resolve_viewer_network_policy(
        bind_host=bind_host,
        port=port,
        trusted_hosts=trusted_hosts,
        trusted_origins=trusted_origins,
        authorization=authorization,
        unsafe_allow_unauthenticated=unsafe_allow_unauthenticated,
        root_path=root_path,
    )


def _app(
    tmp_path: Path,
    policy: ViewerNetworkPolicy,
    *,
    root_path: str = "",
) -> ASGIApp:
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir(parents=True)
    (dist_dir / "index.html").write_text(
        "<html><head></head><body>viewer</body></html>",
        encoding="utf-8",
    )
    return standalone_view_app(
        view_config=ViewConfig(),
        network_policy=policy,
        root_path=root_path,
        directory=dist_dir,
    )


def _assert_framing_headers(response: Response) -> None:
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
    assert response.headers["x-frame-options"] == "DENY"


def _base64url(value: str) -> str:
    return base64.urlsafe_b64encode(value.encode()).decode().rstrip("=")


def test_loopback_policy_defaults() -> None:
    policy = _policy()
    assert Authority("127.0.0.1", 7576) in policy.trusted_hosts
    assert Authority("localhost", 7576) in policy.trusted_hosts
    assert Origin("http", Authority("127.0.0.1", 7576)) in policy.trusted_origins
    assert Origin("http", Authority("localhost", 7576)) in policy.trusted_origins


def test_custom_loopback_dns_origin_adds_host_authority() -> None:
    policy = _policy(trusted_origins=("HTTP://My-Scout.:7576/",))
    authority = Authority("my-scout", 7576)
    assert authority in policy.trusted_hosts
    assert Origin("http", authority) in policy.trusted_origins


def test_absolute_root_path_supplies_compatibility_origin() -> None:
    policy = _policy(root_path="https://scout.example/proxy/")
    origin = Origin("https", Authority("scout.example"))
    assert origin in policy.trusted_origins
    assert origin.authority in policy.trusted_hosts


def test_explicit_origin_takes_precedence_over_absolute_root_path() -> None:
    policy = _policy(
        trusted_origins=("https://configured.example",),
        root_path="https://root-path.example/proxy/",
    )
    assert Origin("https", Authority("configured.example")) in policy.trusted_origins
    assert Origin("https", Authority("root-path.example")) not in policy.trusted_origins


def test_path_only_root_path_does_not_widen_trust() -> None:
    policy = _policy(root_path="/proxy")
    assert Origin("https", Authority("scout.example")) not in policy.trusted_origins


def test_trusted_host_does_not_authorize_browser_origin() -> None:
    policy = _policy(trusted_hosts=("health.internal:7576",))
    authority = Authority("health.internal", 7576)
    assert authority in policy.trusted_hosts
    assert Origin("http", authority) not in policy.trusted_origins


@pytest.mark.parametrize(
    "origin",
    [
        "null",
        "ftp://scout.example",
        "http://user@scout.example",
        "http://scout.example/path",
        "http://scout.example?query",
        "http://scout.example#fragment",
        "http://*.scout.example",
        "http://scout_example",
        "http://scout.example:",
        "http://scout.example:0",
        "http://scout.example:65536",
    ],
)
def test_invalid_trusted_origins_rejected(origin: str) -> None:
    with pytest.raises(ViewerNetworkPolicyError):
        _policy(trusted_origins=(origin,))


@pytest.mark.parametrize(
    "host",
    [
        "*.scout.example",
        "scout.example/path",
        "user@scout.example",
        "scout_example",
        "[::1",
        "::1",
        "scout.example:0",
        "scout.example:65536",
    ],
)
def test_invalid_trusted_hosts_rejected(host: str) -> None:
    with pytest.raises(ViewerNetworkPolicyError):
        _policy(trusted_hosts=(host,))


def test_non_loopback_and_wildcard_startup_policy() -> None:
    with pytest.raises(ViewerNetworkPolicyError, match="without request authorization"):
        _policy(bind_host="192.0.2.10")

    with pytest.raises(ViewerNetworkPolicyError, match="explicit trusted"):
        _policy(bind_host="0.0.0.0", authorization="secret")

    policy = _policy(
        bind_host="0.0.0.0",
        authorization="secret",
        root_path="https://scout.example/proxy/",
    )
    assert Origin("https", Authority("scout.example")) in policy.trusted_origins


def test_explicit_unsafe_non_loopback_policy_warns() -> None:
    policy = _policy(
        bind_host="0.0.0.0",
        trusted_origins=("http://192.0.2.10:7576",),
        unsafe_allow_unauthenticated=True,
    )
    warning = unsafe_network_warning(policy)
    assert warning is not None
    assert "0.0.0.0:7576" in warning
    assert "Any network client" in warning


def test_attacker_selected_host_rejected_for_document_and_api(
    tmp_path: Path,
) -> None:
    app = _app(tmp_path, _policy())
    with TestClient(app, base_url="http://localhost:7576") as client:
        document = client.get("/", headers={"Host": "rebind.test:7576"})
        api = client.get(
            "/api/v2/app-config",
            headers={
                "Host": "rebind.test:7576",
                "Origin": "http://rebind.test:7576",
                "Sec-Fetch-Site": "same-origin",
            },
        )

    assert document.status_code == 400
    assert api.status_code == 400
    _assert_framing_headers(document)
    _assert_framing_headers(api)


def test_duplicate_host_headers_are_rejected(tmp_path: Path) -> None:
    app = _app(tmp_path, _policy())
    with TestClient(app, base_url="http://localhost:7576") as client:
        response = client.get(
            "/",
            headers=[
                ("Host", "localhost:7576"),
                ("Host", "rebind.test:7576"),
            ],
        )

    assert response.status_code == 400


def test_matching_loopback_host_and_origin_can_read_api(tmp_path: Path) -> None:
    app = _app(tmp_path, _policy())
    with TestClient(app, base_url="http://localhost:7576") as client:
        with_origin = client.get(
            "/api/v2/app-config",
            headers={
                "Origin": "http://localhost:7576",
                "Sec-Fetch-Site": "same-origin",
            },
        )
        without_origin = client.get(
            "/api/v2/app-config",
            headers={"Sec-Fetch-Site": "same-origin"},
        )

    assert with_origin.status_code == 200
    assert without_origin.status_code == 200
    assert "access-control-allow-origin" not in with_origin.headers


def test_custom_loopback_dns_origin_is_configurable(tmp_path: Path) -> None:
    trusted_app = _app(
        tmp_path / "trusted",
        _policy(trusted_origins=("http://my-scout:7576",)),
    )
    with TestClient(trusted_app, base_url="http://my-scout:7576") as client:
        trusted = client.get(
            "/api/v2/app-config",
            headers={"Origin": "http://my-scout:7576"},
        )

    untrusted_app = _app(tmp_path / "untrusted", _policy())
    with TestClient(untrusted_app, base_url="http://my-scout:7576") as client:
        untrusted = client.get(
            "/api/v2/app-config",
            headers={"Origin": "http://my-scout:7576"},
        )

    assert trusted.status_code == 200
    assert untrusted.status_code == 400


def test_trusted_host_only_rejects_browser_fetch_but_allows_non_browser(
    tmp_path: Path,
) -> None:
    app = _app(
        tmp_path,
        _policy(trusted_hosts=("health.internal:7576",)),
    )
    with TestClient(app, base_url="http://health.internal:7576") as client:
        browser = client.get(
            "/api/v2/app-config",
            headers={"Sec-Fetch-Site": "same-origin"},
        )
        non_browser = client.get("/api/v2/app-config")

    assert browser.status_code == 403
    assert non_browser.status_code == 200


def test_untrusted_or_mismatched_browser_origin_rejected(tmp_path: Path) -> None:
    app = _app(
        tmp_path,
        _policy(
            trusted_origins=(
                "http://my-scout:7576",
                "http://other-scout:7576",
            )
        ),
    )
    with TestClient(app, base_url="http://my-scout:7576") as client:
        attacker = client.get(
            "/api/v2/app-config",
            headers={"Origin": "https://attacker.example"},
        )
        other_trusted_host = client.get(
            "/api/v2/app-config",
            headers={"Origin": "http://other-scout:7576"},
        )

    assert attacker.status_code == 403
    assert other_trusted_host.status_code == 403


def test_origin_scheme_must_match_request_scheme(tmp_path: Path) -> None:
    app = _app(
        tmp_path,
        _policy(trusted_origins=("https://scout.example",)),
    )
    with TestClient(app, base_url="http://scout.example") as client:
        response = client.get(
            "/api/v2/app-config",
            headers={"Origin": "https://scout.example"},
        )

    assert response.status_code == 403


def test_fetch_metadata_and_malformed_origins_are_rejected(
    tmp_path: Path,
) -> None:
    app = _app(tmp_path, _policy())
    with TestClient(app, base_url="http://localhost:7576") as client:
        cross_site = client.get(
            "/api/v2/app-config",
            headers={"Sec-Fetch-Site": "cross-site"},
        )
        same_site = client.get(
            "/api/v2/app-config",
            headers={
                "Origin": "http://localhost:7576",
                "Sec-Fetch-Site": "same-site",
            },
        )
        null_origin = client.get(
            "/api/v2/app-config",
            headers={"Origin": "null"},
        )
        duplicate_origin = client.get(
            "/api/v2/app-config",
            headers=[
                ("Origin", "http://localhost:7576"),
                ("Origin", "https://attacker.example"),
            ],
        )

    assert cross_site.status_code == 403
    assert same_site.status_code == 403
    assert null_origin.status_code == 403
    assert duplicate_origin.status_code == 403


def test_authorized_extension_request_and_whole_app_authorization(
    tmp_path: Path,
) -> None:
    app = _app(tmp_path, _policy(authorization="secret"))
    with TestClient(app, base_url="http://localhost:7576") as client:
        api = client.get(
            "/api/v2/app-config",
            headers={"Authorization": "secret"},
        )
        static = client.get("/", headers={"Authorization": "secret"})
        unauthorized_api = client.get("/api/v2/app-config")
        unauthorized_static = client.get("/")

    assert api.status_code == 200
    assert static.status_code == 200
    assert unauthorized_api.status_code == 401
    assert unauthorized_static.status_code == 401
    _assert_framing_headers(unauthorized_static)


def test_authorization_does_not_bypass_origin_validation(
    tmp_path: Path,
) -> None:
    app = _app(tmp_path, _policy(authorization="secret"))
    with TestClient(app, base_url="http://localhost:7576") as client:
        response = client.get(
            "/api/v2/app-config",
            headers={
                "Authorization": "secret",
                "Origin": "https://attacker.example",
            },
        )

    assert response.status_code == 403


def test_absolute_root_path_reverse_proxy_origin_succeeds(
    tmp_path: Path,
) -> None:
    root_path = "https://scout.example/proxy/"
    policy = _policy(
        bind_host="0.0.0.0",
        authorization="secret",
        root_path=root_path,
    )
    app = _app(tmp_path, policy, root_path=root_path)

    with TestClient(app, base_url="https://scout.example") as client:
        api = client.get(
            "/api/v2/app-config",
            headers={
                "Authorization": "secret",
                "Origin": "https://scout.example",
                "Sec-Fetch-Site": "same-origin",
            },
        )
        static = client.get("/", headers={"Authorization": "secret"})

    assert api.status_code == 200
    assert static.status_code == 200
    assert "window.__SCOUT_BASE_PATH__='/proxy'" in static.text


def test_origin_checks_block_scan_delete_before_handler(
    tmp_path: Path,
) -> None:
    app = _app(tmp_path, _policy())
    delete_url = (
        f"/api/v2/scans/{_base64url(str(tmp_path / 'scans'))}/"
        f"{_base64url(str(tmp_path / 'outside'))}"
    )

    with (
        patch("inspect_scout._view._api_v2_scans.send2trash") as send2trash,
        TestClient(app, base_url="http://localhost:7576") as client,
    ):
        switched = client.delete(
            delete_url,
            headers={
                "Host": "rebind.test:7576",
                "Origin": "http://rebind.test:7576",
                "Sec-Fetch-Site": "same-origin",
            },
        )
        cross_origin = client.delete(
            delete_url,
            headers={"Origin": "https://attacker.example"},
        )

    assert switched.status_code == 400
    assert cross_origin.status_code == 403
    send2trash.assert_not_called()


def test_framing_headers_cover_static_and_error_responses(
    tmp_path: Path,
) -> None:
    app = _app(tmp_path, _policy())
    with TestClient(app, base_url="http://localhost:7576") as client:
        root = client.get("/")
        missing = client.get("/missing")
        forbidden = client.get(
            "/api/v2/app-config",
            headers={"Origin": "https://attacker.example"},
        )

    assert root.status_code == 200
    assert missing.status_code == 404
    assert forbidden.status_code == 403
    _assert_framing_headers(root)
    _assert_framing_headers(missing)
    _assert_framing_headers(forbidden)


def test_unsafe_bind_is_rejected_before_port_acquisition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    view_module = importlib.import_module("inspect_scout._view.view")
    acquired = False

    def acquire_port(_app_dir: Path, _port: int) -> None:
        nonlocal acquired
        acquired = True

    monkeypatch.setattr(view_module, "view_acquire_port", acquire_port)

    with pytest.raises(ViewerNetworkPolicyError):
        view_module.view(
            host="0.0.0.0",
            trusted_origins=("http://192.0.2.10:7576",),
        )

    assert acquired is False


def test_existing_view_positional_parameter_order_is_preserved() -> None:
    view_module = importlib.import_module("inspect_scout._view.view")
    assert list(inspect.signature(view_module.view).parameters)[:11] == [
        "project_dir",
        "transcripts",
        "scans",
        "mode",
        "host",
        "port",
        "browser",
        "authorization",
        "log_level",
        "fs_options",
        "root_path",
    ]
    assert list(inspect.signature(view_server).parameters)[:7] == [
        "config",
        "host",
        "port",
        "mode",
        "authorization",
        "fs_options",
        "root_path",
    ]
