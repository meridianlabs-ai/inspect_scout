"""Redact secrets from messages before they are sent to a scanning model."""

import dataclasses
import re
from collections.abc import Awaitable, Callable
from typing import Any, Literal

from inspect_ai._util.content import (
    Content,
    ContentReasoning,
    ContentText,
    ContentToolUse,
)
from inspect_ai.model import ChatMessage, ChatMessageAssistant, ChatMessageTool

from .extract import MessagesPreprocessor

_SECRET_WORDS = frozenset(
    {
        "token",
        "secret",
        "password",
        "passwd",
        "credential",
        "credentials",
        "dsn",
        "apikey",
    }
)
# Prefixes that make "<prefix>_key" a non-secret (database, cache, or index keys).
_NON_SECRET_KEY_PREFIXES = frozenset(
    {
        "public",
        "primary",
        "foreign",
        "sort",
        "partition",
        "cache",
        "idempotency",
        "composite",
        "unique",
        "natural",
        "row",
        "lookup",
        "group",
        "dict",
        "map",
        "hash",
        "object",
        "s3",
        "translation",
        "i18n",
    }
)
# Final name parts that describe a secret rather than hold it (token_count,
# password_policy, token_type, secret_name).
_NON_SECRET_SUFFIXES = frozenset(
    {
        "count",
        "type",
        "kind",
        "length",
        "len",
        "size",
        "limit",
        "limits",
        "budget",
        "policy",
        "name",
        "names",
        "id",
        "ids",
        "url",
        "endpoint",
        "expiry",
        "expires",
        "ttl",
        "field",
        "label",
        "prompt",
    }
)
_NAME_PARTS = re.compile(r"[A-Z]+(?![a-z])|[A-Z]?[a-z]+|[0-9]+")


def _is_secret_name(name: str) -> bool:
    """Whether a variable, key, or flag name holds a secret.

    Matches names with a secret word as a component in any casing (TOKEN,
    db_password, accessToken, --api-key, PGPASSWORD, DATABASE_URL), and
    ``<prefix>_key`` names (ENCRYPTION_KEY, openaiKey) except database/cache
    keys (primary_key, cache_key). A bare ``key`` or ``auth`` is too common
    ("key: user_id") and does not count, nor do names that describe a secret
    rather than hold it (token_count, password_policy, token_type).
    """
    parts = [p.lower() for p in _NAME_PARTS.findall(name.lstrip("-"))]
    if "databaseurl" in "".join(parts):  # a connection string with credentials
        return True
    if not parts or (len(parts) > 1 and parts[-1] in _NON_SECRET_SUFFIXES):
        return False
    if any(p in _SECRET_WORDS or p.endswith(("password", "passwd")) for p in parts):
        return True
    return any(
        part == "key" and i > 0 and parts[i - 1] not in _NON_SECRET_KEY_PREFIXES
        for i, part in enumerate(parts)
    )


# NAME=value / "name": "value" / --flag=value assignments. The name is matched
# whole and possessively (no backtracking over identifier splits) and checked
# with _is_secret_name in the replacement, which also leaves alone values that
# are variable references or code (${VAR}, $VAR, os.environ[...], getenv(...))
# and plain numbers.
_ASSIGNMENT = re.compile(
    r"(?<![A-Za-z0-9_\-])([A-Za-z0-9_\-]++)(['\"]?)([ \t]*[=:][ \t]*)"
    r"(?:\"([^\"\n]{6,}+)\"|'([^'\n]{6,}+)'|(['\"]?)([^\s'\"]{6,}+))"
)
_CODE_VALUE = re.compile(
    r"^(?:\$\{|\$[A-Za-z_]\w*$|os\.environ|os\.getenv|getenv\(|process\.env|ENV\[)"
)

RedactMode = Literal["keys", "all"]
"""What `redact_secrets()` removes: `"keys"` (keys and credentials) or `"all"` (keys, credentials, and email addresses)."""

_KEY_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "private_key",
        re.compile(
            r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----",
            re.S,
        ),
    ),
    ("typesafe_key", re.compile(r"\bapikey_[A-Za-z0-9_]{20,}")),
    (
        "anthropic_openai_key",
        re.compile(r"\bsk-(?:ant-[a-z0-9]+-|proj-)?[A-Za-z0-9_\-]{20,}"),
    ),
    ("aws_key", re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")),
    ("github_token", re.compile(r"\b(?:ghp|gho|ghs|ghu|github_pat)_[A-Za-z0-9_]{20,}")),
    ("slack_token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}")),
    ("google_key", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")),
    ("stripe_key", re.compile(r"\b(?:sk|rk|pk)_(?:live|test)_[A-Za-z0-9]{16,}")),
    (
        "jwt",
        re.compile(
            r"\beyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}"
        ),
    ),
    ("bearer", re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._\-]{16,}")),
    # "Token <value>" auth headers; the value must contain a digit, so prose
    # like "the token internationalization step" is left alone.
    (
        "token_auth",
        re.compile(r"(?i)\btoken\s+(?=[A-Za-z._\-]*[0-9])[A-Za-z0-9._\-]{16,}"),
    ),
    ("huggingface_token", re.compile(r"\bhf_[A-Za-z0-9]{20,}")),
    ("gitlab_token", re.compile(r"\bglpat-[A-Za-z0-9_\-]{20,}")),
    ("basic_auth", re.compile(r"(?i)\bbasic\s+[A-Za-z0-9+/]{16,}={0,2}")),
    (
        "url_credentials",
        # Anchored and possessive: an unanchored scheme rescans long dotted
        # runs from every word boundary (quadratic time).
        re.compile(
            r"(?i)(?<![a-z0-9+.\-])([a-z][a-z0-9+.\-]*+://)[^\s:/@]++:[^\s/?#]+@"
        ),
    ),
    ("env_assignment", _ASSIGNMENT),
]
_EMAIL_PATTERN = (
    "email",
    re.compile(
        r"(?<![A-Za-z0-9._%+\-])[A-Za-z0-9._%+\-]++@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"
    ),
)


def redact_text(text: str, mode: RedactMode = "keys") -> str:
    """Replace secrets in `text` with `[REDACTED...]` markers.

    Args:
        text: Text to redact.
        mode: `"keys"` removes keys and credentials (private keys, provider API
            keys, JWTs, bearer tokens, credentials in URLs, and values assigned to
            `*KEY`/`*TOKEN`/`*SECRET`/`*PASSWORD`-style variables); `"all"` also
            removes email addresses.

    Returns:
        The redacted text.
    """
    patterns = _KEY_PATTERNS + ([_EMAIL_PATTERN] if mode == "all" else [])
    for name, pattern in patterns:
        text = pattern.sub(_replacement(name), text)
    return text


def redact_secrets(
    mode: RedactMode = "keys",
) -> Callable[[list[ChatMessage]], Awaitable[list[ChatMessage]]]:
    """Message transform that redacts secrets, for use with `MessagesPreprocessor`.

    Redacts message text, reasoning, tool call arguments (including values of
    secret-named arguments such as ``password``), tool errors, and server-side
    tool use. Message ids are preserved, so citations of redacted messages
    still resolve.

    Args:
        mode: ``"keys"`` removes keys and credentials (private keys, provider API
            keys, JWTs, bearer/basic credentials, credentials in URLs, and values
            assigned to ``*KEY``/``*TOKEN``/``*SECRET``/``*PASSWORD``-style names);
            ``"all"`` also removes email addresses.

    Returns:
        A transform for `MessagesPreprocessor(transform=...)`.
    """

    async def transform(messages: list[ChatMessage]) -> list[ChatMessage]:
        return [_redact_message(message, mode) for message in messages]

    return transform


def _redact_message(message: ChatMessage, mode: RedactMode) -> ChatMessage:
    update: dict[str, Any] = {}
    if isinstance(message.content, str):
        update["content"] = redact_text(message.content, mode)
    else:
        update["content"] = [_redact_content(c, mode) for c in message.content]
    if isinstance(message, ChatMessageTool) and message.error is not None:
        update["error"] = dataclasses.replace(
            message.error, message=redact_text(message.error.message, mode)
        )
    if isinstance(message, ChatMessageAssistant) and message.tool_calls:
        update["tool_calls"] = [
            dataclasses.replace(
                call,
                arguments=redact_value(call.arguments, mode),
            )
            for call in message.tool_calls
        ]
    return message.model_copy(update=update)


def redact_value(value: Any, mode: RedactMode, secret_key: str | None = None) -> Any:
    """Redact the strings in a JSON-like value, keeping its structure.

    String values under secret-named keys (e.g. ``password``, ``api_key``) are
    replaced outright, including inside lists and dicts under such a key.
    """
    if isinstance(value, str):
        if secret_key is not None and _is_secret_value(secret_key, value):
            return "[REDACTED]"
        return redact_text(value, mode)
    if isinstance(value, dict):
        return {
            k: redact_value(v, mode, str(k) if _is_secret_name(str(k)) else secret_key)
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [redact_value(v, mode, secret_key) for v in value]
    return value


def _redact_content(content: Content, mode: RedactMode) -> Content:
    if isinstance(content, ContentText):
        return content.model_copy(update={"text": redact_text(content.text, mode)})
    if isinstance(content, ContentReasoning):
        return content.model_copy(
            update={
                "reasoning": redact_text(content.reasoning, mode),
                "summary": redact_text(content.summary, mode)
                if content.summary
                else content.summary,
            }
        )
    if isinstance(content, ContentToolUse):
        return content.model_copy(
            update={
                "arguments": redact_text(content.arguments, mode),
                "result": redact_text(content.result, mode),
                "error": redact_text(content.error, mode)
                if content.error
                else content.error,
            }
        )
    return content


def _is_secret_value(name: str, value: str) -> bool:
    """Whether `value`, assigned to `name`, is a secret to redact."""
    return (
        bool(value)
        and _is_secret_name(name)
        and not value.isdigit()
        and not _CODE_VALUE.match(value)
    )


def _replacement(name: str) -> Callable[[re.Match[str]], str]:
    def replace(match: re.Match[str]) -> str:
        if name == "env_assignment":
            key, key_quote, separator = match.group(1, 2, 3)
            double, single, opening, bare = match.group(4, 5, 6, 7)
            value = double or single or bare or ""
            if not _is_secret_value(key, value):
                return match.group(0)
            if double is not None:
                return f'{key}{key_quote}{separator}"[REDACTED]"'
            if single is not None:
                return f"{key}{key_quote}{separator}'[REDACTED]'"
            return f"{key}{key_quote}{separator}{opening or ''}[REDACTED]"
        if name == "url_credentials":
            return f"{match.group(1)}[REDACTED]@"
        return f"[REDACTED_{name.upper()}]"

    return replace


def redacting_preprocessor(
    preprocessor: MessagesPreprocessor[list[ChatMessage]] | None,
    redact: RedactMode | Literal[False],
) -> MessagesPreprocessor[list[ChatMessage]] | None:
    """Add `redact_secrets()` after any transform of `preprocessor`.

    Args:
        preprocessor: The scanner's message preprocessor (or `None` for the default).
        redact: What to redact, or `False` to return `preprocessor` unchanged.

    Returns:
        A preprocessor with the same options whose transform also redacts.
    """
    if redact is False:
        return preprocessor
    if redact not in ("keys", "all"):
        raise ValueError(f'redact must be "keys", "all", or False (got {redact!r}).')
    base = preprocessor or MessagesPreprocessor[list[ChatMessage]]()
    redactor = redact_secrets(redact)
    inner = base.transform

    async def transform(messages: list[ChatMessage]) -> list[ChatMessage]:
        return await redactor(await inner(messages) if inner is not None else messages)

    return dataclasses.replace(base, transform=transform)
