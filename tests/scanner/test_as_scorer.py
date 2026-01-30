from inspect_ai import Task, eval
from inspect_ai.event import ModelEvent, ToolEvent
from inspect_ai.model import ChatMessage, ChatMessageAssistant, ChatMessageUser
from inspect_ai.scorer import mean
from inspect_scout._scanner.result import Result
from inspect_scout._scanner.scanner import Scanner, ScannerConfig, scanner
from inspect_scout._scanner.scorer import _scanner_messages_and_events, as_scorer
from inspect_scout._transcript.types import Transcript, TranscriptContent


@scanner(messages="all")
def my_scanner() -> Scanner[Transcript]:
    async def scan(_transcript: Transcript) -> Result:
        return Result(value=1)

    return scan


def test_scanner_as_scorer_explicit() -> None:
    task = Task(scorer=as_scorer(my_scanner()))
    log = eval(tasks=task, model="mockllm/model")[0]
    assert log.status == "success"


def test_scanner_as_scorer_implicit() -> None:
    task = Task(scorer=my_scanner())
    log = eval(tasks=task, model="mockllm/model")[0]
    assert log.status == "success"


# Resultset tests


@scanner(messages="all")
def single_result_scanner() -> Scanner[Transcript]:
    """Scanner that returns a resultset with a single result."""

    async def scan(_transcript: Transcript) -> list[Result]:
        return [Result(label="finding", value=True)]

    return scan


@scanner(messages="all")
def multiple_unique_labels_scanner() -> Scanner[Transcript]:
    """Scanner that returns a resultset with multiple unique labels."""

    async def scan(_transcript: Transcript) -> list[Result]:
        return [
            Result(label="deception", value=True),
            Result(label="jailbreak", value=False),
            Result(label="misconfig", value=True),
        ]

    return scan


@scanner(messages="all")
def duplicate_labels_scanner() -> Scanner[Transcript]:
    """Scanner that returns a resultset with duplicate labels (takes first)."""

    async def scan(_transcript: Transcript) -> list[Result]:
        return [
            Result(label="deception", value=True, explanation="First finding"),
            Result(label="jailbreak", value=False),
            Result(label="deception", value=False, explanation="Second finding"),
        ]

    return scan


@scanner(messages="all")
def complex_values_scanner() -> Scanner[Transcript]:
    """Scanner that returns a resultset with complex values (lists, dicts)."""

    async def scan(_transcript: Transcript) -> list[Result]:
        return [
            Result(label="items", value=["a", "b", "c"]),
            Result(label="config", value={"key": "value", "count": 42}),
            Result(label="simple", value=True),
        ]

    return scan


@scanner(messages="all")
def empty_resultset_scanner() -> Scanner[Transcript]:
    """Scanner that returns an empty resultset."""

    async def scan(_transcript: Transcript) -> list[Result]:
        return []

    return scan


@scanner(messages="all")
def unlabeled_result_scanner() -> Scanner[Transcript]:
    """Scanner that returns a resultset with missing label (should error)."""

    async def scan(_transcript: Transcript) -> list[Result]:
        return [
            Result(value=True),  # No label
        ]

    return scan


def test_resultset_single_result() -> None:
    """Test that a resultset with a single result produces a dict-valued score."""
    task = Task(scorer=as_scorer(single_result_scanner(), metrics={"*": [mean()]}))
    log = eval(tasks=task, model="mockllm/model")[0]
    assert log.status == "success"
    # Check that the score value is a dict with the expected label
    assert log.samples is not None
    sample = log.samples[0]
    assert sample.scores is not None
    score = sample.scores["single_result_scanner"]
    assert isinstance(score.value, dict)
    assert score.value == {"finding": True}


def test_resultset_multiple_unique_labels() -> None:
    """Test that a resultset with multiple unique labels produces correct dict."""
    task = Task(
        scorer=as_scorer(multiple_unique_labels_scanner(), metrics={"*": [mean()]})
    )
    log = eval(tasks=task, model="mockllm/model")[0]
    assert log.status == "success"
    assert log.samples is not None
    sample = log.samples[0]
    assert sample.scores is not None
    score = sample.scores["multiple_unique_labels_scanner"]
    assert isinstance(score.value, dict)
    assert score.value == {
        "deception": True,
        "jailbreak": False,
        "misconfig": True,
    }


def test_resultset_duplicate_labels_takes_first() -> None:
    """Test that duplicate labels take the first occurrence."""
    task = Task(scorer=as_scorer(duplicate_labels_scanner(), metrics={"*": [mean()]}))
    log = eval(tasks=task, model="mockllm/model")[0]
    assert log.status == "success"
    assert log.samples is not None
    sample = log.samples[0]
    assert sample.scores is not None
    score = sample.scores["duplicate_labels_scanner"]
    assert isinstance(score.value, dict)
    # Should have the first "deception" value (True), not the second (False)
    assert score.value == {
        "deception": True,  # First occurrence
        "jailbreak": False,
    }


def test_resultset_complex_values_serialized() -> None:
    """Test that complex values (lists, dicts) are JSON-serialized."""
    task = Task(scorer=as_scorer(complex_values_scanner(), metrics={"*": [mean()]}))
    log = eval(tasks=task, model="mockllm/model")[0]
    assert log.status == "success"
    assert log.samples is not None
    sample = log.samples[0]
    assert sample.scores is not None
    score = sample.scores["complex_values_scanner"]
    assert isinstance(score.value, dict)
    # Complex values should be serialized as JSON strings
    assert "items" in score.value
    assert isinstance(score.value["items"], str)
    assert "config" in score.value
    assert isinstance(score.value["config"], str)
    # Simple values remain as-is
    assert score.value["simple"] is True


def test_resultset_empty() -> None:
    """Test that an empty resultset produces an empty dict."""
    task = Task(scorer=as_scorer(empty_resultset_scanner(), metrics={"*": [mean()]}))
    log = eval(tasks=task, model="mockllm/model")[0]
    assert log.status == "success"
    assert log.samples is not None
    sample = log.samples[0]
    assert sample.scores is not None
    score = sample.scores["empty_resultset_scanner"]
    assert isinstance(score.value, dict)
    assert score.value == {}


def test_resultset_unlabeled_result_raises_error() -> None:
    """Test that a resultset with unlabeled results raises an error when used as a scorer."""
    task = Task(scorer=as_scorer(unlabeled_result_scanner()))
    log = eval(tasks=task, model="mockllm/model")[0]
    # The eval should complete but with an error status
    assert log.status == "error"
    # The error should be about unlabeled result
    assert log.samples is not None
    sample = log.samples[0]
    assert sample.error is not None
    assert "must have labels" in str(sample.error.message)


# Tests for _scanner_messages_and_events filtering


from datetime import datetime

from inspect_ai.event._model import ModelEvent
from inspect_ai.event._tool import ToolEvent
from inspect_ai.model import (
    ChatMessageSystem,
    ChatMessageTool,
    GenerateConfig,
    ModelOutput,
)


def _make_messages() -> list[ChatMessage]:
    """Create a sample list of messages for testing."""
    return [
        ChatMessageSystem(content="You are a helpful assistant."),
        ChatMessageUser(content="Hello, can you help me?"),
        ChatMessageAssistant(content="Of course! How can I help?"),
        ChatMessageUser(content="What is 2+2?"),
        ChatMessageAssistant(content="2+2 equals 4."),
        ChatMessageTool(content="tool result", tool_call_id="tool-1"),
    ]


def _make_model_event(uuid: str) -> ModelEvent:
    """Create a model event for testing."""
    return ModelEvent(
        event="model",
        timestamp=datetime.now(),
        model="gpt-4",
        input=[],
        tools=[],
        tool_choice="auto",
        config=GenerateConfig(),
        output=ModelOutput(model="gpt-4", choices=[], completion="test"),
        uuid=uuid,
    )


def _make_tool_event(uuid: str) -> ToolEvent:
    """Create a tool event for testing."""
    return ToolEvent(
        event="tool",
        timestamp=datetime.now(),
        id="tool-call-id",
        function="test_func",
        arguments={"arg": "value"},
        result="result",
        uuid=uuid,
    )


def _make_events() -> list[ModelEvent | ToolEvent]:
    """Create a sample list of events for testing."""
    return [
        _make_model_event("model-1"),
        _make_tool_event("tool-1"),
        _make_model_event("model-2"),
        _make_tool_event("tool-2"),
    ]


class TestScannerMessagesAndEvents:
    """Tests for _scanner_messages_and_events filtering function."""

    def test_messages_all_returns_all_messages(self) -> None:
        """Test that messages='all' returns all messages."""
        config = ScannerConfig(content=TranscriptContent(messages="all", events=None))
        messages = _make_messages()
        events = _make_events()

        result_messages, result_events = _scanner_messages_and_events(
            config, messages, events
        )

        assert len(result_messages) == 6
        assert result_messages == messages
        assert result_events == []

    def test_events_all_returns_all_events(self) -> None:
        """Test that events='all' returns all events."""
        config = ScannerConfig(content=TranscriptContent(messages=None, events="all"))
        messages = _make_messages()
        events = _make_events()

        result_messages, result_events = _scanner_messages_and_events(
            config, messages, events
        )

        assert result_messages == []
        assert len(result_events) == 4
        assert result_events == events

    def test_messages_filter_by_role(self) -> None:
        """Test filtering messages by specific roles."""
        config = ScannerConfig(
            content=TranscriptContent(messages=["user", "assistant"], events=None)
        )
        messages = _make_messages()
        events = _make_events()

        result_messages, result_events = _scanner_messages_and_events(
            config, messages, events
        )

        # Should have 2 user + 2 assistant = 4 messages
        assert len(result_messages) == 4
        assert all(m.role in ("user", "assistant") for m in result_messages)
        assert result_events == []

    def test_messages_filter_single_role(self) -> None:
        """Test filtering messages by a single role."""
        config = ScannerConfig(
            content=TranscriptContent(messages=["assistant"], events=None)
        )
        messages = _make_messages()
        events = _make_events()

        result_messages, result_events = _scanner_messages_and_events(
            config, messages, events
        )

        # Should have 2 assistant messages
        assert len(result_messages) == 2
        assert all(m.role == "assistant" for m in result_messages)

    def test_events_filter_by_type(self) -> None:
        """Test filtering events by specific types."""
        config = ScannerConfig(
            content=TranscriptContent(messages=None, events=["tool"])
        )
        messages = _make_messages()
        events = _make_events()

        result_messages, result_events = _scanner_messages_and_events(
            config, messages, events
        )

        assert result_messages == []
        # Should have 2 tool events
        assert len(result_events) == 2
        assert all(e.event == "tool" for e in result_events)

    def test_events_filter_model_only(self) -> None:
        """Test filtering for only model events."""
        config = ScannerConfig(
            content=TranscriptContent(messages=None, events=["model"])
        )
        messages = _make_messages()
        events = _make_events()

        result_messages, result_events = _scanner_messages_and_events(
            config, messages, events
        )

        # Should have 2 model events
        assert len(result_events) == 2
        assert all(e.event == "model" for e in result_events)

    def test_messages_none_returns_empty(self) -> None:
        """Test that messages=None returns empty list."""
        config = ScannerConfig(content=TranscriptContent(messages=None, events=None))
        messages = _make_messages()
        events = _make_events()

        result_messages, result_events = _scanner_messages_and_events(
            config, messages, events
        )

        assert result_messages == []
        assert result_events == []

    def test_combined_filtering(self) -> None:
        """Test filtering both messages and events simultaneously."""
        config = ScannerConfig(
            content=TranscriptContent(messages=["assistant"], events=["tool"])
        )
        messages = _make_messages()
        events = _make_events()

        result_messages, result_events = _scanner_messages_and_events(
            config, messages, events
        )

        # Should have 2 assistant messages and 2 tool events
        assert len(result_messages) == 2
        assert all(m.role == "assistant" for m in result_messages)
        assert len(result_events) == 2
        assert all(e.event == "tool" for e in result_events)

    def test_all_messages_all_events(self) -> None:
        """Test that both 'all' returns everything."""
        config = ScannerConfig(content=TranscriptContent(messages="all", events="all"))
        messages = _make_messages()
        events = _make_events()

        result_messages, result_events = _scanner_messages_and_events(
            config, messages, events
        )

        assert result_messages == messages
        assert result_events == events

    def test_empty_inputs(self) -> None:
        """Test with empty message and event lists."""
        config = ScannerConfig(content=TranscriptContent(messages="all", events="all"))
        messages: list[ChatMessage] = []
        events: list[ModelEvent | ToolEvent] = []

        result_messages, result_events = _scanner_messages_and_events(
            config, messages, events
        )

        assert result_messages == []
        assert result_events == []

    def test_filter_nonexistent_role_returns_empty(self) -> None:
        """Test filtering for a role that doesn't exist in messages."""
        config = ScannerConfig(
            content=TranscriptContent(messages=["system"], events=None)
        )
        # Create messages without system role
        messages = [
            ChatMessageUser(content="Hello"),
            ChatMessageAssistant(content="Hi"),
        ]
        events = _make_events()

        result_messages, result_events = _scanner_messages_and_events(
            config, messages, events
        )

        assert result_messages == []


# Full pipeline tests for message/event filtering


@scanner(messages=["assistant"])
def assistant_only_scanner() -> Scanner[Transcript]:
    """Scanner that only receives assistant messages."""

    async def scan(transcript: Transcript) -> Result:
        # Count messages and verify they are all assistant messages
        message_count = len(transcript.messages)
        all_assistant = all(m.role == "assistant" for m in transcript.messages)
        return Result(
            value=message_count if all_assistant else -1,
            explanation=f"Received {message_count} messages, all assistant: {all_assistant}",
        )

    return scan


@scanner(messages=["user", "assistant"])
def user_assistant_scanner() -> Scanner[Transcript]:
    """Scanner that receives only user and assistant messages."""

    async def scan(transcript: Transcript) -> Result:
        # Count by role
        user_count = sum(1 for m in transcript.messages if m.role == "user")
        assistant_count = sum(1 for m in transcript.messages if m.role == "assistant")
        # Verify no other roles
        other_count = sum(
            1 for m in transcript.messages if m.role not in ("user", "assistant")
        )
        return Result(
            value=user_count + assistant_count if other_count == 0 else -1,
            metadata={"user": user_count, "assistant": assistant_count, "other": other_count},
        )

    return scan


def test_assistant_only_filter_full_pipeline() -> None:
    """Test that scanner with messages=['assistant'] only receives assistant messages."""
    task = Task(scorer=as_scorer(assistant_only_scanner()))
    log = eval(tasks=task, model="mockllm/model")[0]
    assert log.status == "success"
    assert log.samples is not None
    sample = log.samples[0]
    assert sample.scores is not None
    score = sample.scores["assistant_only_scanner"]
    # Score value should be positive (count of assistant messages)
    # and not -1 (which would indicate non-assistant messages were received)
    assert isinstance(score.value, int | float)
    assert score.value >= 0, "Scanner received non-assistant messages"


def test_user_assistant_filter_full_pipeline() -> None:
    """Test that scanner with messages=['user', 'assistant'] only receives those roles."""
    task = Task(scorer=as_scorer(user_assistant_scanner()))
    log = eval(tasks=task, model="mockllm/model")[0]
    assert log.status == "success"
    assert log.samples is not None
    sample = log.samples[0]
    assert sample.scores is not None
    score = sample.scores["user_assistant_scanner"]
    # Score value should be positive (count of user+assistant messages)
    # and not -1 (which would indicate other roles were received)
    assert isinstance(score.value, int | float)
    assert score.value >= 0, "Scanner received messages with unexpected roles"
    # Check metadata confirms no 'other' roles
    if score.metadata:
        assert score.metadata.get("other", 0) == 0
