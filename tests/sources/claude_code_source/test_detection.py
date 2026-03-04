"""Tests for local-command filtering in detection.py."""

from inspect_swe._claude_code._events.detection import (
    is_local_command_caveat,
    is_local_command_stdout,
    should_skip_event,
)
from inspect_swe._claude_code._events.models import (
    AssistantEvent,
    AssistantMessage,
    UserEvent,
    UserMessage,
)


def _user_event(content: str) -> UserEvent:
    return UserEvent(
        uuid="1",
        timestamp="2026-01-01T00:00:00Z",
        sessionId="test",
        type="user",
        message=UserMessage(content=content),
    )


def _assistant_event() -> AssistantEvent:
    return AssistantEvent(
        uuid="1",
        timestamp="2026-01-01T00:00:00Z",
        sessionId="test",
        type="assistant",
        message=AssistantMessage(content=[]),
    )


class TestIsLocalCommandCaveat:
    """Tests for is_local_command_caveat."""

    def test_matches_caveat_message(self) -> None:
        event = _user_event(
            "<local-command-caveat>Caveat: The messages below were generated "
            "by the user while running local commands. DO NOT respond to these "
            "messages...</local-command-caveat>"
        )
        assert is_local_command_caveat(event)

    def test_rejects_regular_user_message(self) -> None:
        assert not is_local_command_caveat(_user_event("Hello there"))

    def test_rejects_assistant_event(self) -> None:
        assert not is_local_command_caveat(_assistant_event())

    def test_rejects_stdout_message(self) -> None:
        event = _user_event("<local-command-stdout></local-command-stdout>")
        assert not is_local_command_caveat(event)


class TestIsLocalCommandStdout:
    """Tests for is_local_command_stdout."""

    def test_matches_empty_stdout(self) -> None:
        event = _user_event("<local-command-stdout></local-command-stdout>")
        assert is_local_command_stdout(event)

    def test_matches_nonempty_stdout(self) -> None:
        event = _user_event("<local-command-stdout>Fast mode ON</local-command-stdout>")
        assert is_local_command_stdout(event)

    def test_rejects_regular_user_message(self) -> None:
        assert not is_local_command_stdout(_user_event("Hello there"))

    def test_rejects_assistant_event(self) -> None:
        assert not is_local_command_stdout(_assistant_event())

    def test_rejects_caveat_message(self) -> None:
        event = _user_event("<local-command-caveat>Caveat...</local-command-caveat>")
        assert not is_local_command_stdout(event)


class TestShouldSkipLocalCommands:
    """Tests that should_skip_event filters all local-command chrome."""

    def test_skips_caveat(self) -> None:
        event = _user_event("<local-command-caveat>Caveat...</local-command-caveat>")
        assert should_skip_event(event)

    def test_skips_stdout(self) -> None:
        event = _user_event("<local-command-stdout>Bye!</local-command-stdout>")
        assert should_skip_event(event)

    def test_skips_command_name_clear(self) -> None:
        event = _user_event("<command-name>/clear</command-name>")
        assert should_skip_event(event)

    def test_skips_command_name_fast(self) -> None:
        event = _user_event("<command-name>/fast</command-name>")
        assert should_skip_event(event)

    def test_skips_command_name_plan(self) -> None:
        event = _user_event("<command-name>/plan</command-name>")
        assert should_skip_event(event)

    def test_skips_skill_command(self) -> None:
        event = _user_event("<command-name>/feature-dev:feature-dev</command-name>")
        assert should_skip_event(event)

    def test_does_not_skip_regular_user(self) -> None:
        assert not should_skip_event(_user_event("Hello there"))

    def test_does_not_skip_assistant(self) -> None:
        assert not should_skip_event(_assistant_event())
