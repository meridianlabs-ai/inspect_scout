"""redact_secrets(): keys and credentials (and optionally emails) are removed."""

import time

import pytest
from inspect_ai._util.content import ContentToolUse
from inspect_ai.model import (
    ChatMessage,
    ChatMessageAssistant,
    ChatMessageTool,
    ChatMessageUser,
)
from inspect_ai.tool import ToolCall, ToolCallError
from inspect_scout import redact_secrets
from inspect_scout._scanner.redact import redact_text, redact_value


@pytest.mark.parametrize(
    "text,secret",
    [
        (
            "export OPENAI_API_KEY=sk-proj-abcdefghijklmnopqrstuvwx",
            "sk-proj-abcdefghijklmnopqrstuvwx",
        ),
        (
            "key sk-ant-api03-abcdefghijklmnopqrstuvwxyz",
            "sk-ant-api03-abcdefghijklmnopqrstuvwxyz",
        ),
        ("AKIAABCDEFGHIJKLMNOP is the id", "AKIAABCDEFGHIJKLMNOP"),
        (
            "token ghp_abcdefghijklmnopqrstuvwxyz0123",
            "ghp_abcdefghijklmnopqrstuvwxyz0123",
        ),
        ("Authorization: Bearer abcdefghijklmnop1234", "abcdefghijklmnop1234"),
        ("postgres://admin:hunter22@db.internal/app", "admin:hunter22"),
        ('DATABASE_URL="postgresql://u@h/d"', "postgresql://u@h/d"),
        ("SECRET_TOKEN: s3cr3tvalue", "s3cr3tvalue"),
        (
            "jwt eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N",
            "eyJhbGciOiJIUzI1NiJ9",
        ),
        (
            "-----BEGIN RSA PRIVATE KEY-----\nMIIabc\n-----END RSA PRIVATE KEY-----",
            "MIIabc",
        ),
    ],
)
def test_keys_are_redacted(text: str, secret: str) -> None:
    assert secret not in redact_text(text)


@pytest.mark.parametrize(
    "text",
    [
        "rm -rf /Users/dev/project/src/components",
        "commit 6491b31f2a9e8d7c6b5a4f3e2d1c0b9a8f7e6d5c",
        "the KEY point is that tests pass",
        "user@example.com wrote this",
        "The monkey: bananas",
        'token = os.environ["X"]',
        "password=${DB_PASS}",
        "token_count: 1234567",
        "key: user_id_column",
        "auth: required",
        "PWD=/home/user/project",
        "token:\n  description: foo",
        "tokenizer: gpt2-large",
        "passwordless: enabled",
        "primary_key: user_id_col",
        "token_type: bearer",
        "password_policy: strict",
        "the token internationalization step",
    ],
)
def test_ordinary_text_is_kept_in_keys_mode(text: str) -> None:
    assert redact_text(text) == text


@pytest.mark.parametrize(
    "text,secret",
    [
        ('{"api_key": "abcd1234efgh5678"}', "abcd1234efgh5678"),
        ("Authorization: Basic dXNlcjpwYXNzd29yZDEyMw==", "dXNlcjpwYXNzd29yZDEyMw=="),
        ("auth_token=abcdef123456 next", "abcdef123456"),
        ('DB_PASSWORD="p@ss w0rd"', "p@ss w0rd"),
        ('"token": "abcdefgh', "abcdefgh"),
        ('{"accessToken": "abcd1234efgh5678ijkl"}', "abcd1234efgh5678ijkl"),
        ("PGPASSWORD=hunter2secret", "hunter2secret"),
        ("mysql --password=hunter2secret", "hunter2secret"),
        ("curl --api-key=abcd1234efgh5678", "abcd1234efgh5678"),
        ("DB_PASSWORD=Xk9#mP2$vL(q8zz", "Xk9#mP2$vL(q8zz"),
        ("Authorization: Token abcd1234efgh5678ijkl", "abcd1234efgh5678ijkl"),
        ("hf_abcdefghijklmnopqrstuvwxyz12", "hf_abcdefghijklmnopqrstuvwxyz12"),
        ("glpat-abcdefghijklmnopqrst12", "glpat-abcdefghijklmnopqrst12"),
        ("postgres://user:p@ss@host/db", "p@ss"),
        ("ENCRYPTION_KEY=abcdef123456", "abcdef123456"),
        ("openaiKey: abcdef123456", "abcdef123456"),
        ('PASSWORD="it\'s secret"', "it's secret"),
        ("API_TOKEN=abc[12]{x}defg", "abc[12]{x}defg"),
    ],
)
def test_more_secret_shapes(text: str, secret: str) -> None:
    assert secret not in redact_text(text)


def test_all_mode_also_redacts_emails() -> None:
    assert "user@example.com" not in redact_text("mail user@example.com", "all")


@pytest.mark.asyncio
async def test_transform_redacts_text_and_tool_arguments_keeping_ids() -> None:
    messages: list[ChatMessage] = [
        ChatMessageUser(content="TOKEN=abcdef123456", id="u1"),
        ChatMessageAssistant(
            content="setting env",
            id="a1",
            tool_calls=[
                ToolCall(
                    id="c1",
                    function="bash",
                    arguments={"cmd": 'export API_KEY="xyz12345678" && run', "n": 3},
                )
            ],
        ),
    ]
    redacted = await redact_secrets()(messages)
    assert [m.id for m in redacted] == ["u1", "a1"]
    assert "abcdef123456" not in redacted[0].text
    assistant = redacted[1]
    assert isinstance(assistant, ChatMessageAssistant) and assistant.tool_calls
    arguments = assistant.tool_calls[0].arguments
    assert "xyz12345678" not in arguments["cmd"]
    assert arguments["n"] == 3


@pytest.mark.asyncio
async def test_transform_redacts_secret_named_arguments_and_tool_output() -> None:
    messages: list[ChatMessage] = [
        ChatMessageAssistant(
            content="",
            id="a1",
            tool_calls=[
                ToolCall(
                    id="c1", function="login", arguments={"password": "hunter22xx"}
                )
            ],
        ),
        ChatMessageTool(
            content="ok",
            id="t1",
            tool_call_id="c1",
            error=ToolCallError(type="unknown", message="PASSWORD=hunter22xx rejected"),
        ),
        ChatMessageAssistant(
            content=[
                ContentToolUse(
                    tool_type="code_execution",
                    id="u1",
                    name="python",
                    arguments="API_KEY='abcdef123456'",
                    result="SECRET=zyxwvu987654",
                )
            ],
            id="a2",
        ),
    ]
    redacted = await redact_secrets()(messages)
    text = repr(redacted)
    for secret in ("hunter22xx", "abcdef123456", "zyxwvu987654"):
        assert secret not in text


def test_long_identifiers_redact_in_linear_time() -> None:
    start = time.perf_counter()
    redact_text("KEY_" * 5000 + "=")
    redact_text("a_" * 50000)
    redact_text("a." * 50000, "all")
    redact_text("x@" * 30000, "all")
    assert time.perf_counter() - start < 1.0


def test_secret_named_arguments_keep_numbers_and_references() -> None:
    redacted = redact_value(
        {"encryption_key": "abcdef123456", "token_count": "12", "password": "${PW}"},
        "keys",
    )
    assert redacted == {
        "encryption_key": "[REDACTED]",
        "token_count": "12",
        "password": "${PW}",
    }


def test_values_nested_under_secret_named_keys_are_redacted() -> None:
    redacted = redact_value(
        {
            "credentials": {"pw": "hunter2hunter2", "ref": "${PW}"},
            "api_key": ["abcdef123456"],
            "config": {"name": "demo", "auth_token": ["zyxwvu987654"]},
        },
        "keys",
    )
    assert redacted == {
        "credentials": {"pw": "[REDACTED]", "ref": "${PW}"},
        "api_key": ["[REDACTED]"],
        "config": {"name": "demo", "auth_token": ["[REDACTED]"]},
    }
