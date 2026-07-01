"""OpenClaw telemetry-hal sessionKey classification and identity.

A ``sessionKey`` (as carried on telemetry-hal events) is
``agent:<agentName>:<kind>[:<channel>...]:<sessionId>``.
The helpers here read role/identity out of that key (and out of spawn results),
keeping that knowledge in one place for the parser to draw on.
"""

from __future__ import annotations

import json

# Session-kind classification (sessionKey = agent:<...>:<kind>:<uuid>).
# ``main``/``telegram``/``dashboard`` are orchestrator surfaces (terminal, the
# Telegram channel, and the web dashboard respectively); ``subagent`` is
# delegated work.
ORCH_KINDS = ("telegram", "main", "dashboard")  # the orchestrator

_REDACTED = "[REMOVED]"


def session_kind(session_key: str) -> str:
    """Role segment of a sessionKey: ``agent:main:subagent:<uuid>`` -> ``subagent``.

    Returns ``""`` if malformed (<3 segments).
    """
    parts = (session_key or "").split(":")
    return parts[2] if len(parts) >= 3 else ""


def session_id_from_session_key(session_key: str) -> str | None:
    """Session/surface identity from an orchestrator sessionKey, or ``None``.

    sessionKey is ``agent:<agentName>:<kind>[:<channel>...]:<sessionId>``. The
    identifying token is the trailing segment: a per-run session id for
    ``main``/``dashboard`` surfaces (``agent:main:dashboard:<uuid>``) but a chat
    id **shared across runs** for ``telegram``
    (``agent:main:telegram:default:direct:<chatId>``). It is therefore not a run
    id — telemetry-hal events carry no runId at all — so the caller must not use
    it as a per-run identifier without further disambiguation.

    Returns ``None`` when no real id is present — a kind-only key
    (``agent:main:main``) or a scrubbed id (``[REMOVED]``) — so the caller falls
    back to the file stem. (``agentName`` is a constant like ``main`` and is
    never an id, which is why the leading segment is not used.)
    """
    parts = (session_key or "").split(":")
    if len(parts) < 4:
        return None  # e.g. agent:main:main — agent name + kind only, no id
    tail = parts[-1].strip()
    if not tail or tail == _REDACTED:
        return None
    return tail


def child_session_key_of(result_text: str) -> str | None:
    """Extract ``childSessionKey`` from a ``sessions_spawn`` tool result JSON."""
    try:
        parsed = json.loads(result_text)
    except (json.JSONDecodeError, TypeError):
        return None
    if isinstance(parsed, dict):
        csk = parsed.get("childSessionKey")
        return str(csk) if csk else None
    return None
