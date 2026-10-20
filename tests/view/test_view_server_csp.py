import json
import re
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from inspect_scout._view._csp import (
    ContentSecurityPolicyError,
    inline_script_source,
    read_content_security_policy,
)
from inspect_scout._view.network import resolve_viewer_network_policy
from inspect_scout._view.server import _ScoutStaticFiles, _view_app
from starlette.types import ASGIApp

_INDEX_SCRIPT = "window.theme = 1;"
_DIRECTIVES = {
    "default-src": ["'none'"],
    "script-src": ["'self'", inline_script_source(_INDEX_SCRIPT)],
    "worker-src": ["'self'"],
}


def _dist(tmp_path: Path, directives: object | None = _DIRECTIVES) -> Path:
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text(
        f"<html><head><script>{_INDEX_SCRIPT}</script></head><body></body></html>"
    )
    (dist / "assets" / "json-parse.worker.js").write_text("self.x = 1;")
    if directives is not None:
        (dist / "content-security-policy.json").write_text(
            json.dumps({"version": 1, "directives": directives})
        )
    return dist


def _api() -> FastAPI:
    api = FastAPI()

    @api.get("/ping")
    def ping() -> dict[str, str]:
        return {"ok": "yes"}

    return api


_PORT = 7576
_BASE_URL = f"http://127.0.0.1:{_PORT}"


def _app(dist: Path, root_path: str = "") -> ASGIApp:
    policy = resolve_viewer_network_policy(bind_host="127.0.0.1", port=_PORT)
    return _view_app(_api(), dist, root_path, policy)


def _client(
    tmp_path: Path, root_path: str = "", directives: object | None = _DIRECTIVES
) -> TestClient:
    app = _app(_dist(tmp_path, directives), root_path)
    return TestClient(app, base_url=_BASE_URL, root_path=root_path)


_POLICY = "default-src 'none'; script-src 'self' {hash}; worker-src 'self'".format(
    hash=inline_script_source(_INDEX_SCRIPT)
)


@pytest.mark.parametrize("path", ["/", "/index.html", "/assets/json-parse.worker.js"])
def test_viewer_files_get_the_dist_policy_and_forbid_framing(
    tmp_path: Path, path: str
) -> None:
    response = _client(tmp_path).get(path)

    assert response.status_code == 200
    assert response.headers["content-security-policy"] == (
        f"{_POLICY}; frame-ancestors 'none'"
    )
    assert response.headers["x-frame-options"] == "DENY"


def test_the_api_only_forbids_framing(tmp_path: Path) -> None:
    response = _client(tmp_path).get("/api/v2/ping")

    assert response.json() == {"ok": "yes"}
    assert response.headers["content-security-policy"] == "frame-ancestors 'none'"
    assert response.headers["x-frame-options"] == "DENY"


# The policy is chosen before routing, and the static mount resolves `..`.
@pytest.mark.parametrize("path", ["/api/..%2f/", "/api/..%2findex.html", "/api"])
def test_api_lookalike_paths_that_reach_the_viewer_get_its_policy(
    tmp_path: Path, path: str
) -> None:
    response = _client(tmp_path).get(path)

    assert response.headers["content-security-policy"] == (
        f"{_POLICY}; frame-ancestors 'none'"
    )


def test_a_server_error_outside_the_api_still_forbids_framing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail(*_: object) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(_ScoutStaticFiles, "get_response", fail)
    app = _app(_dist(tmp_path))

    response = TestClient(app, base_url=_BASE_URL, raise_server_exceptions=False).get(
        "/"
    )

    assert response.status_code == 500
    assert response.headers["content-security-policy"] == (
        f"{_POLICY}; frame-ancestors 'none'"
    )
    assert response.headers["x-frame-options"] == "DENY"


def test_a_dist_without_a_policy_only_forbids_framing(tmp_path: Path) -> None:
    response = _client(tmp_path, directives=None).get("/")

    assert response.headers["content-security-policy"] == "frame-ancestors 'none'"


def test_behind_a_proxy_the_policy_allows_the_injected_base_path_script(
    tmp_path: Path,
) -> None:
    response = _client(tmp_path, root_path="/proxy/scout").get("/proxy/scout/")

    scripts = re.findall(r"<script>(.*?)</script>", response.text)
    injected = [script for script in scripts if "__SCOUT_BASE_PATH__" in script]
    assert len(injected) == 1
    script_src = next(
        directive
        for directive in response.headers["content-security-policy"].split("; ")
        if directive.startswith("script-src ")
    ).split(" ")[1:]
    # Every inline script on the page is allowed, the server's included.
    assert all(inline_script_source(script) in script_src for script in scripts)
    assert script_src[0] == "'self'"


def test_the_api_behind_a_proxy_only_forbids_framing(tmp_path: Path) -> None:
    response = _client(tmp_path, root_path="/proxy/scout").get(
        "/proxy/scout/api/v2/ping"
    )

    assert response.headers["content-security-policy"] == "frame-ancestors 'none'"


def test_a_malformed_policy_fails_the_server_at_startup(tmp_path: Path) -> None:
    with pytest.raises(ContentSecurityPolicyError):
        _app(_dist(tmp_path, directives=["not", "an", "object"]))


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("not json", "Invalid viewer"),
        ('{"version": 2, "directives": {"a": []}}', "unsupported version"),
        ('{"version": true, "directives": {"a": []}}', "unsupported version"),
        ('{"version": 1, "directives": {}}', "non-empty object"),
        (
            '{"version": 1, "directives": {"a": [], "a": []}}',
            "duplicate key",
        ),
        (
            '{"version": 1, "directives": {"img-src": [], "IMG-SRC": []}}',
            "duplicate directive",
        ),
        (
            '{"version": 1, "directives": {"frame-ancestors": ["\'none\'"]}}',
            "set by the host",
        ),
        ('{"version": 1, "directives": {"img-src": ["a b"]}}', "disallowed"),
        ('{"version": 1, "directives": {"img-src": ["a;b"]}}', "disallowed"),
        ('{"version": 1, "directives": {"img-src": ["a,b"]}}', "disallowed"),
        ('{"version": 1, "directives": {"img-src": "a"}}', "list of sources"),
    ],
)
def test_rejects_a_malformed_policy_file(
    tmp_path: Path, text: str, message: str
) -> None:
    (tmp_path / "content-security-policy.json").write_text(text)

    with pytest.raises(ContentSecurityPolicyError, match=message):
        read_content_security_policy(tmp_path)


def test_a_server_script_needs_a_script_src_to_join(tmp_path: Path) -> None:
    (tmp_path / "content-security-policy.json").write_text(
        '{"version": 1, "directives": {"default-src": ["\'none\'"]}}'
    )

    with pytest.raises(ContentSecurityPolicyError, match="no 'script-src'"):
        read_content_security_policy(tmp_path, extra_script_sources=("'sha256-x'",))


def test_an_empty_source_list_is_a_value_less_directive(tmp_path: Path) -> None:
    (tmp_path / "content-security-policy.json").write_text(
        '{"version": 1, "directives": {"upgrade-insecure-requests": [], '
        '"default-src": ["\'none\'"]}}'
    )

    assert (
        read_content_security_policy(tmp_path)
        == "upgrade-insecure-requests; default-src 'none'"
    )
