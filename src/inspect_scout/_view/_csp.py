"""The viewer's Content-Security-Policy, as `scout view` delivers it.

The viewer build emits its policy as `content-security-policy.json` rather
than baking it into `index.html` (the VS Code extension reads the same
`index.html` and delivers its own translation), so the view server sends it
as a header. Its `sha256` sources hash the inline scripts of that same
dist's `index.html`, so a policy is only valid for the dist it was read from.

Mirrors `inspect_ai._view._csp` and `inspect_ai._view.network`; switch to
those once Scout requires an inspect_ai release that ships them.
"""

import base64
import hashlib
import json
from pathlib import Path
from typing import Any

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

CSP_FILENAME = "content-security-policy.json"
CSP_VERSION = 1

_FRAME_ANCESTORS_NONE = "frame-ancestors 'none'"

# The host owns framing: the view server appends its own `frame-ancestors`.
_HOST_OWNED_DIRECTIVES = frozenset({"frame-ancestors"})


class ContentSecurityPolicyError(ValueError):
    """A viewer dist contains a malformed Content-Security-Policy file."""


def inline_script_source(code: str) -> str:
    """The `script-src` source that allows an inline `<script>` with `code`."""
    digest = base64.b64encode(hashlib.sha256(code.encode("utf-8")).digest())
    return f"'sha256-{digest.decode('ascii')}'"


def read_content_security_policy(
    dist_dir: Path, extra_script_sources: tuple[str, ...] = ()
) -> str | None:
    """Read the viewer Content-Security-Policy from a dist directory.

    Args:
        dist_dir: Local directory containing the built viewer (`index.html`).
        extra_script_sources: `script-src` sources for inline scripts the
            server adds to `index.html` (see `inline_script_source`).

    Returns:
        The policy string (directives in file order, each name followed by
        its space-separated sources, joined with `"; "`), or `None` if the
        dist has no policy file (a viewer built before the policy existed).

    Raises:
        ContentSecurityPolicyError: If the policy file is present but
            malformed. The dist is trusted build output, so this indicates a
            broken build rather than something to silently ignore.
    """
    policy_file = dist_dir / CSP_FILENAME
    if not policy_file.exists():
        return None

    try:
        data = json.loads(
            policy_file.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
        )
        return _policy_string(data, extra_script_sources)
    except (UnicodeDecodeError, ValueError) as ex:
        raise ContentSecurityPolicyError(
            f"Invalid viewer Content-Security-Policy file {policy_file}: {ex}"
        ) from ex


def _policy_string(data: Any, extra_script_sources: tuple[str, ...]) -> str:
    if not isinstance(data, dict):
        raise ValueError("expected a JSON object")

    version = data.get("version")
    if type(version) is not int or version != CSP_VERSION:
        raise ValueError(f"unsupported version {version!r} (expected {CSP_VERSION})")

    directives = data.get("directives")
    if not isinstance(directives, dict) or not directives:
        raise ValueError("'directives' must be a non-empty object")

    seen: set[str] = set()
    parts: list[str] = []
    for name, sources in directives.items():
        _validate_token(name, "directive name")
        folded = name.lower()
        if folded in seen:
            raise ValueError(f"duplicate directive {name!r}")
        seen.add(folded)
        if folded in _HOST_OWNED_DIRECTIVES:
            raise ValueError(f"directive {name!r} is set by the host, not the dist")

        # An empty list is a value-less directive (`upgrade-insecure-requests`).
        if not isinstance(sources, list):
            raise ValueError(f"directive {name!r} must have a list of sources")
        for source in sources:
            _validate_token(source, f"source in directive {name!r}")
        if folded == "script-src":
            sources = [*sources, *extra_script_sources]

        parts.append(" ".join([name, *sources]))

    if extra_script_sources and "script-src" not in seen:
        raise ValueError("no 'script-src' to allow the server's inline script")

    return "; ".join(parts)


def _validate_token(value: Any, label: str) -> None:
    """Require a non-empty string of printable, non-space ASCII other than `;` and `,`.

    Whitespace would split a token, `;` would start a new directive, `,`
    would start a new policy, and control or non-ASCII characters can't be
    carried in a header value.
    """
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} must be a non-empty string, got {value!r}")
    if any(not 0x21 <= ord(char) <= 0x7E or char in ";," for char in value):
        raise ValueError(f"{label} {value!r} contains a disallowed character")


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate key {key!r}")
        result[key] = value
    return result


class SecurityHeadersMiddleware:
    """Add framing and Content-Security-Policy headers to every HTTP response.

    Every response gets `frame-ancestors 'none'` and `X-Frame-Options: DENY`.
    The viewer's own policy is added to every other response too, not just
    `index.html`: a worker script takes its policy from its own response
    headers. Mounted apps such as the JSON API (whose docs pages load scripts
    from a CDN) are exempt and keep only `frame-ancestors`.

    Exemptions are matched before routing, so they must cover only paths the
    router sends to the exempt app. Exempt exactly the mount path: a broader
    prefix (`/api` for an app mounted at `/api/v2`) also exempts paths such
    as `/api/..%2f/` that reach the static mount, which resolves the `..`. A
    mounted app is exempt for every path under `{mount}/`, which holds as
    long as it is mounted before the static mount.

    Args:
        app: The ASGI app to wrap.
        content_security_policy: The policy of the viewer dist being served
            (see `read_content_security_policy`), or `None` for a dist without
            one.
        viewer_policy_exempt_mounts: Mount paths (such as `/api`) whose
            sub-paths don't get the viewer policy.
    """

    def __init__(
        self,
        app: ASGIApp,
        content_security_policy: str | None = None,
        viewer_policy_exempt_mounts: tuple[str, ...] = (),
    ) -> None:
        self.app = app
        self._viewer_policy = (
            f"{content_security_policy}; {_FRAME_ANCESTORS_NONE}"
            if content_security_policy is not None
            else _FRAME_ANCESTORS_NONE
        )
        self._exempt_prefixes = tuple(
            f"{mount.rstrip('/')}/" for mount in viewer_policy_exempt_mounts
        )

    def _policy_for(self, path: str) -> str:
        if path.startswith(self._exempt_prefixes):
            return _FRAME_ANCESTORS_NONE
        return self._viewer_policy

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = str(scope.get("path", ""))
        root_path = str(scope.get("root_path", ""))
        if root_path and path.startswith(root_path):
            path = path[len(root_path) :]
        policy = self._policy_for(path)

        async def send_with_security_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers.append("Content-Security-Policy", policy)
                headers["X-Frame-Options"] = "DENY"
            await send(message)

        await self.app(scope, receive, send_with_security_headers)
