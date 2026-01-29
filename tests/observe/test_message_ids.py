"""Tests for MessageIdManager and message ID stability."""

from inspect_ai.event._model import ModelEvent
from inspect_ai.model import (
    ChatMessage,
    ChatMessageAssistant,
    ChatMessageUser,
    GenerateConfig,
    ModelOutput,
)
from inspect_scout._util.message_ids import (
    MessageIdManager,
    apply_message_ids_to_event,
)


class TestMessageIdManager:
    """Tests for MessageIdManager."""

    def test_same_content_same_id(self) -> None:
        """Messages with identical content get the same ID."""
        manager = MessageIdManager()
        msg1 = ChatMessageUser(content="Hello")
        msg2 = ChatMessageUser(content="Hello")  # Same content

        id1 = manager.get_id(msg1, [])
        id2 = manager.get_id(msg2, [])

        assert id1 == id2

    def test_different_content_different_id(self) -> None:
        """Messages with different content get different IDs."""
        manager = MessageIdManager()
        msg1 = ChatMessageUser(content="Hello")
        msg2 = ChatMessageUser(content="Goodbye")

        id1 = manager.get_id(msg1, [])
        id2 = manager.get_id(msg2, [])

        assert id1 != id2

    def test_duplicate_in_conversation_gets_new_id(self) -> None:
        """Same content appearing twice in same conversation gets different IDs."""
        manager = MessageIdManager()
        msg1 = ChatMessageUser(content="Hello")
        msg2 = ChatMessageUser(content="Hello")  # Same content

        # First message in empty conversation
        msg1.id = manager.get_id(msg1, [])

        # Second message with first in conversation
        msg2.id = manager.get_id(msg2, [msg1])

        # Should be different since msg1's ID is already in conversation
        assert msg1.id != msg2.id

    def test_reuse_across_conversations(self) -> None:
        """Same content in different conversations can reuse IDs."""
        manager = MessageIdManager()
        msg1 = ChatMessageUser(content="Hello")
        msg2 = ChatMessageUser(content="Hello")  # Same content

        # First conversation
        id1 = manager.get_id(msg1, [])

        # Different conversation (empty context)
        id2 = manager.get_id(msg2, [])

        # Should reuse the same ID
        assert id1 == id2

    def test_apply_ids_basic(self) -> None:
        """apply_ids assigns IDs to all messages."""
        manager = MessageIdManager()
        messages: list[ChatMessage] = [
            ChatMessageUser(content="Hello"),
            ChatMessageAssistant(content="Hi there!"),
            ChatMessageUser(content="How are you?"),
        ]

        manager.apply_ids(messages)

        # All messages should have IDs
        for msg in messages:
            assert msg.id is not None
            assert len(msg.id) > 0

        # All IDs should be unique within this conversation
        ids = [msg.id for msg in messages]
        assert len(ids) == len(set(ids))

    def test_apply_ids_duplicate_content(self) -> None:
        """apply_ids handles duplicate content correctly."""
        manager = MessageIdManager()
        messages: list[ChatMessage] = [
            ChatMessageUser(content="Hello"),
            ChatMessageAssistant(content="Hi!"),
            ChatMessageUser(content="Hello"),  # Same as first
        ]

        manager.apply_ids(messages)

        # First and third messages have same content but should have different IDs
        # because they're in the same conversation
        assert messages[0].id != messages[2].id

    def test_cross_event_stability(self) -> None:
        """Same message appearing in multiple events gets same ID."""
        manager = MessageIdManager()

        # First event: just user message
        event1_messages: list[ChatMessage] = [ChatMessageUser(content="Hello")]
        manager.apply_ids(event1_messages)
        user_id_event1 = event1_messages[0].id

        # Second event: user message + assistant response + user followup
        event2_messages: list[ChatMessage] = [
            ChatMessageUser(content="Hello"),  # Same as before
            ChatMessageAssistant(content="Hi there!"),
            ChatMessageUser(content="How are you?"),
        ]
        manager.apply_ids(event2_messages)
        user_id_event2 = event2_messages[0].id

        # The "Hello" message should have the same ID across events
        assert user_id_event1 == user_id_event2

    def test_different_roles_different_ids(self) -> None:
        """Same text but different roles gets different IDs."""
        manager = MessageIdManager()
        user_msg = ChatMessageUser(content="Hello")
        assistant_msg = ChatMessageAssistant(content="Hello")

        id1 = manager.get_id(user_msg, [])
        id2 = manager.get_id(assistant_msg, [])

        assert id1 != id2


class TestApplyMessageIdsToEvent:
    """Tests for apply_message_ids_to_event helper."""

    def test_applies_ids_to_input(self) -> None:
        """IDs are applied to input messages."""
        manager = MessageIdManager()
        event = ModelEvent(
            model="test-model",
            input=[
                ChatMessageUser(content="Hello"),
                ChatMessageAssistant(content="Hi!"),
            ],
            tools=[],
            tool_choice="auto",
            config=GenerateConfig(),
            output=ModelOutput.from_message(
                ChatMessageAssistant(content="Response"),
            ),
        )

        apply_message_ids_to_event(event, manager)

        # Input messages should have IDs
        for msg in event.input:
            assert msg.id is not None

    def test_applies_id_to_output(self) -> None:
        """ID is applied to output message."""
        manager = MessageIdManager()
        event = ModelEvent(
            model="test-model",
            input=[ChatMessageUser(content="Hello")],
            tools=[],
            tool_choice="auto",
            config=GenerateConfig(),
            output=ModelOutput.from_message(
                ChatMessageAssistant(content="Response"),
            ),
        )

        apply_message_ids_to_event(event, manager)

        # Output message should have an ID
        assert event.output is not None
        assert isinstance(event.output, ModelOutput)
        assert event.output.message is not None
        assert event.output.message.id is not None

    def test_output_id_distinct_from_input(self) -> None:
        """Output message ID is distinct from input message IDs."""
        manager = MessageIdManager()
        event = ModelEvent(
            model="test-model",
            input=[ChatMessageUser(content="Hello")],
            tools=[],
            tool_choice="auto",
            config=GenerateConfig(),
            output=ModelOutput.from_message(
                ChatMessageAssistant(content="Hi there!"),
            ),
        )

        apply_message_ids_to_event(event, manager)

        input_ids = {msg.id for msg in event.input}
        assert event.output is not None
        assert isinstance(event.output, ModelOutput)
        assert event.output.message is not None
        output_id = event.output.message.id

        assert output_id not in input_ids

    def test_multi_event_stability(self) -> None:
        """Messages appearing in multiple events maintain stable IDs."""
        manager = MessageIdManager()

        # First event
        event1 = ModelEvent(
            model="test-model",
            input=[ChatMessageUser(content="Hello")],
            tools=[],
            tool_choice="auto",
            config=GenerateConfig(),
            output=ModelOutput.from_message(
                ChatMessageAssistant(content="Hi!"),
            ),
        )
        apply_message_ids_to_event(event1, manager)

        # Store IDs from first event
        user_id_1 = list(event1.input)[0].id
        assert event1.output is not None
        assert isinstance(event1.output, ModelOutput)
        assert event1.output.message is not None
        assistant_id_1 = event1.output.message.id

        # Second event includes messages from first event
        event2 = ModelEvent(
            model="test-model",
            input=[
                ChatMessageUser(content="Hello"),  # Same as event1
                ChatMessageAssistant(content="Hi!"),  # Same as event1 output
                ChatMessageUser(content="How are you?"),  # New message
            ],
            tools=[],
            tool_choice="auto",
            config=GenerateConfig(),
            output=ModelOutput.from_message(
                ChatMessageAssistant(content="I'm good!"),
            ),
        )
        apply_message_ids_to_event(event2, manager)

        # Same content should have same IDs
        input_list = list(event2.input)
        assert input_list[0].id == user_id_1  # "Hello" user message
        assert input_list[1].id == assistant_id_1  # "Hi!" assistant message

        # New message should have new ID
        assert input_list[2].id is not None
        assert input_list[2].id not in {user_id_1, assistant_id_1}

    def test_handles_output_without_choices(self) -> None:
        """Handles events with output but no choices gracefully."""
        manager = MessageIdManager()
        event = ModelEvent(
            model="test-model",
            input=[ChatMessageUser(content="Hello")],
            tools=[],
            tool_choice="auto",
            config=GenerateConfig(),
            output=ModelOutput(model="test-model", choices=[]),
        )

        # Should not raise
        apply_message_ids_to_event(event, manager)

        # Input should still have IDs
        assert list(event.input)[0].id is not None
