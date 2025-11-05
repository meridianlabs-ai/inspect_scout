"""Tests for message extraction functions in llm_scanner."""

import pytest
from inspect_ai._util.content import (
    ContentData,
    ContentDocument,
    ContentImage,
    ContentReasoning,
    ContentText,
)
from inspect_ai.model import (
    ChatMessage,
    ChatMessageAssistant,
    ChatMessageSystem,
    ChatMessageTool,
    ChatMessageUser,
)
from inspect_ai.tool import ToolCall, ToolCallError
from inspect_scout._scanner.extract import (
    ContentFilter,
    message_as_str,
    messages_as_str,
)


@pytest.mark.parametrize(
    "message,expected",
    [
        # Basic user message
        (
            ChatMessageUser(content="Hello, world!"),
            "user:\nHello, world!\n",
        ),
        # Basic assistant message
        (
            ChatMessageAssistant(content="I can help with that."),
            "assistant:\nI can help with that.\n",
        ),
        # Basic tool message
        (
            ChatMessageTool(content="Operation successful", function="write_file"),
            "tool:\nOperation successful",
        ),
        # Message with whitespace gets stripped
        (
            ChatMessageUser(content="  \n  Hello  \n  "),
            "user:\n  \n  Hello  \n  \n",
        ),
        # Message with empty content
        (
            ChatMessageUser(content=""),
            "user:\n\n",
        ),
    ],
)
def test_simple_messages(message: ChatMessage, expected: str) -> None:
    """Simple messages produce expected formatted output."""
    result = message_as_str(message)
    assert result == expected


@pytest.mark.parametrize(
    "content,function,error_message,expected",
    [
        # Tool error with function name
        (
            "Error occurred",
            "get_weather",
            "Connection timeout",
            "tool:\nError occurred\n\nError in tool call 'get_weather':\nConnection timeout\n",
        ),
        # Tool error without function name
        (
            "Something went wrong",
            None,
            "Unknown error",
            "tool:\nSomething went wrong\n\nError in tool call 'unknown':\nUnknown error\n",
        ),
        # Tool error with empty content
        (
            "",
            "read_file",
            "Access denied",
            "tool:\n\n\nError in tool call 'read_file':\nAccess denied\n",
        ),
    ],
)
def test_tool_messages_with_errors(
    content: str,
    function: str | None,
    error_message: str,
    expected: str,
) -> None:
    """Tool messages with errors include error information."""
    error = ToolCallError(type="unknown", message=error_message)
    message = ChatMessageTool(content=content, function=function, error=error)
    result = message_as_str(message)
    assert result == expected


@pytest.mark.parametrize(
    "message,expected",
    [
        # Single tool call with dict arguments
        (
            ChatMessageAssistant(
                content="Let me check the weather.",
                tool_calls=[
                    ToolCall(
                        id="call_1",
                        function="get_weather",
                        arguments={"location": "San Francisco", "units": "celsius"},
                    )
                ],
            ),
            "assistant:\nLet me check the weather.\n\n"
            "Tool Call: get_weather\nArguments:\n"
            "location: San Francisco\nunits: celsius",
        ),
        # Multiple tool calls
        (
            ChatMessageAssistant(
                content="Let me check both.",
                tool_calls=[
                    ToolCall(
                        id="call_1",
                        function="get_weather",
                        arguments={"location": "San Francisco"},
                    ),
                    ToolCall(
                        id="call_2",
                        function="get_time",
                        arguments={"timezone": "PST"},
                    ),
                ],
            ),
            "assistant:\nLet me check both.\n\n"
            "Tool Call: get_weather\nArguments:\nlocation: San Francisco\n"
            "Tool Call: get_time\nArguments:\ntimezone: PST",
        ),
        # Tool call with empty arguments
        (
            ChatMessageAssistant(
                content="Calling with no args.",
                tool_calls=[
                    ToolCall(id="call_1", function="no_args_function", arguments={})
                ],
            ),
            "assistant:\nCalling with no args.\n\nTool Call: no_args_function\nArguments:\n",
        ),
        # Tool call with empty content
        (
            ChatMessageAssistant(
                content="",
                tool_calls=[
                    ToolCall(
                        id="call_1", function="search", arguments={"query": "test"}
                    )
                ],
            ),
            "assistant:\n\n\nTool Call: search\nArguments:\nquery: test",
        ),
        # Tool call with nested arguments
        (
            ChatMessageAssistant(
                content="Running complex call.",
                tool_calls=[
                    ToolCall(
                        id="call_1",
                        function="complex_function",
                        arguments={
                            "config": {"retry": True, "timeout": 30},
                            "items": ["item1", "item2"],
                        },
                    )
                ],
            ),
            "assistant:\nRunning complex call.\n\n"
            "Tool Call: complex_function\nArguments:\n"
            "config: {'retry': True, 'timeout': 30}\n"
            "items: ['item1', 'item2']",
        ),
    ],
)
def test_assistant_messages_with_tool_calls(
    message: ChatMessageAssistant, expected: str
) -> None:
    """Assistant messages with tool calls format calls and arguments."""
    result = message_as_str(message)
    assert result == expected


@pytest.mark.parametrize(
    "message,expected",
    [
        # Multiple text content parts joined with newlines
        (
            ChatMessageUser(
                content=[
                    ContentText(text="First text"),
                    ContentText(text="Second text"),
                ]
            ),
            "user:\nFirst text\nSecond text\n",
        ),
        # Mixed content - text extracted, non-text ignored
        (
            ChatMessageUser(
                content=[
                    ContentText(text="Text before image"),
                    ContentImage(image="data:image/png;base64,abc"),
                    ContentText(text="Text after image"),
                ]
            ),
            "user:\nText before image\n<image />\nText after image\n",
        ),
        # Only non-text content produces empty text
        (
            ChatMessageUser(content=[ContentImage(image="data:image/png;base64,abc")]),
            "user:\n<image />\n",
        ),
        # Reasoning + text (reasoning is not type='text' so excluded)
        (
            ChatMessageAssistant(
                content=[
                    ContentReasoning(reasoning="Let me think..."),
                    ContentText(text="The answer is 42"),
                ]
            ),
            "assistant:\n\n<think>Let me think...</think>\nThe answer is 42\n",
        ),
        # Text mixed with various content types
        (
            ChatMessageUser(
                content=[
                    ContentText(text="Start"),
                    ContentData(data={"key": "value"}),
                    ContentText(text="Middle"),
                    ContentDocument(document="data:application/pdf;base64,xyz"),
                    ContentText(text="End"),
                ]
            ),
            "user:\nStart\n<data />\nMiddle\n<document />\nEnd\n",
        ),
        # Content with whitespace in text parts - strips outer, not inner
        (
            ChatMessageUser(
                content=[
                    ContentText(text="  Text with spaces  "),
                    ContentText(text="\n\nText with newlines\n\n"),
                ]
            ),
            "user:\n  Text with spaces  \n\n\nText with newlines\n\n\n",
        ),
        # Tool message with list content
        (
            ChatMessageTool(
                content=[
                    ContentText(text="Tool result"),
                    ContentImage(image="data:image/png;base64,abc"),
                ],
                function="analyze",
            ),
            "tool:\nTool result\n<image />",
        ),
        # Assistant with list content and tool calls
        (
            ChatMessageAssistant(
                content=[
                    ContentText(text="Let me search"),
                    ContentImage(image="data:image/png;base64,abc"),
                    ContentText(text="for that"),
                ],
                tool_calls=[
                    ToolCall(
                        id="call_1", function="search", arguments={"query": "test"}
                    )
                ],
            ),
            "assistant:\nLet me search\n<image />\nfor that\n\n"
            "Tool Call: search\nArguments:\nquery: test",
        ),
        # Tool message with list content and error
        (
            ChatMessageTool(
                content=[
                    ContentText(text="Attempted operation"),
                    ContentData(data={"status": "failed"}),
                ],
                function="slow_operation",
                error=ToolCallError(type="timeout", message="Operation timed out"),
            ),
            "tool:\nAttempted operation\n<data />\n\nError in tool call 'slow_operation':\nOperation timed out\n",
        ),
    ],
)
def test_messages_with_list_content(message: ChatMessage, expected: str) -> None:
    """Messages with list[Content] extract only text content parts."""
    result = message_as_str(message)
    assert result == expected


@pytest.mark.parametrize(
    "message,exclude_tool_usage,exclude_reasoning,expected",
    [
        # Tool calls only: excluded with string content
        (
            ChatMessageAssistant(
                content="Let me check the weather.",
                tool_calls=[
                    ToolCall(
                        id="call_1",
                        function="get_weather",
                        arguments={"location": "San Francisco"},
                    )
                ],
            ),
            True,
            False,
            "assistant:\nLet me check the weather.\n",
        ),
        # Tool calls only: excluded with multiple calls
        (
            ChatMessageAssistant(
                content="Let me check both.",
                tool_calls=[
                    ToolCall(id="call_1", function="get_weather", arguments={}),
                    ToolCall(id="call_2", function="get_time", arguments={}),
                ],
            ),
            True,
            False,
            "assistant:\nLet me check both.\n",
        ),
        # Tool calls only: included (default)
        (
            ChatMessageAssistant(
                content="Using tools.",
                tool_calls=[
                    ToolCall(id="call_1", function="search", arguments={"q": "test"})
                ],
            ),
            False,
            False,
            "assistant:\nUsing tools.\n\nTool Call: search\nArguments:\nq: test",
        ),
        # Tool calls only: excluded with empty content
        (
            ChatMessageAssistant(
                content="",
                tool_calls=[
                    ToolCall(id="call_1", function="search", arguments={"q": "test"})
                ],
            ),
            True,
            False,
            "assistant:\n\n",
        ),
        # Tool calls only: excluded with list content
        (
            ChatMessageAssistant(
                content=[
                    ContentText(text="Searching"),
                    ContentImage(image="data:image/png;base64,abc"),
                ],
                tool_calls=[
                    ToolCall(id="call_1", function="search", arguments={"q": "test"})
                ],
            ),
            True,
            False,
            "assistant:\nSearching\n<image />\n",
        ),
        # Reasoning only: included (exclude=False)
        (
            ChatMessageAssistant(
                content=[
                    ContentReasoning(reasoning="Let me think..."),
                    ContentText(text="The answer is 42"),
                ]
            ),
            False,
            False,
            "assistant:\n\n<think>Let me think...</think>\nThe answer is 42\n",
        ),
        # Reasoning only: excluded (default, exclude=True)
        (
            ChatMessageAssistant(
                content=[
                    ContentReasoning(reasoning="Let me think..."),
                    ContentText(text="The answer is 42"),
                ]
            ),
            False,
            True,
            "assistant:\nThe answer is 42\n",
        ),
        # Reasoning only: only reasoning content, included
        (
            ChatMessageAssistant(content=[ContentReasoning(reasoning="Thinking...")]),
            False,
            False,
            "assistant:\n\n<think>Thinking...</think>\n",
        ),
        # Reasoning only: only reasoning content, excluded (default)
        (
            ChatMessageAssistant(content=[ContentReasoning(reasoning="Thinking...")]),
            False,
            True,
            "assistant:\n\n",
        ),
        # Reasoning only: multiple reasoning parts, included
        (
            ChatMessageAssistant(
                content=[
                    ContentReasoning(reasoning="First thought"),
                    ContentText(text="Answer"),
                    ContentReasoning(reasoning="Second thought"),
                ]
            ),
            False,
            False,
            "assistant:\n\n<think>First thought</think>\nAnswer\n\n<think>Second thought</think>\n",
        ),
        # Reasoning only: multiple reasoning parts, excluded (default)
        (
            ChatMessageAssistant(
                content=[
                    ContentReasoning(reasoning="First thought"),
                    ContentText(text="Answer"),
                    ContentReasoning(reasoning="Second thought"),
                ]
            ),
            False,
            True,
            "assistant:\nAnswer\n",
        ),
        # Combined: both excluded
        (
            ChatMessageAssistant(
                content=[
                    ContentReasoning(reasoning="Let me think"),
                    ContentText(text="Answer"),
                ],
                tool_calls=[
                    ToolCall(id="call_1", function="search", arguments={"q": "test"})
                ],
            ),
            True,
            True,
            "assistant:\nAnswer\n",
        ),
        # Combined: both included
        (
            ChatMessageAssistant(
                content=[
                    ContentReasoning(reasoning="Let me think"),
                    ContentText(text="Answer"),
                ],
                tool_calls=[
                    ToolCall(id="call_1", function="search", arguments={"q": "test"})
                ],
            ),
            False,
            False,
            "assistant:\n\n<think>Let me think</think>\nAnswer\n\n"
            "Tool Call: search\nArguments:\nq: test",
        ),
        # Combined: only reasoning included (tool calls excluded)
        (
            ChatMessageAssistant(
                content=[
                    ContentReasoning(reasoning="Thinking"),
                    ContentText(text="Done"),
                ],
                tool_calls=[ToolCall(id="call_1", function="act", arguments={})],
            ),
            True,
            False,
            "assistant:\n\n<think>Thinking</think>\nDone\n",
        ),
        # Combined: only tool calls included (reasoning excluded, default)
        (
            ChatMessageAssistant(
                content=[
                    ContentReasoning(reasoning="Thinking"),
                    ContentText(text="Done"),
                ],
                tool_calls=[ToolCall(id="call_1", function="act", arguments={})],
            ),
            False,
            True,
            "assistant:\nDone\n\nTool Call: act\nArguments:\n",
        ),
        # Combined: both excluded, only reasoning and tool calls in content
        (
            ChatMessageAssistant(
                content=[ContentReasoning(reasoning="Only thinking")],
                tool_calls=[ToolCall(id="call_1", function="act", arguments={})],
            ),
            True,
            True,
            "assistant:\n\n",
        ),
    ],
)
def test_exclude_parameters(
    message: ChatMessageAssistant,
    exclude_tool_usage: bool,
    exclude_reasoning: bool,
    expected: str,
) -> None:
    """Test exclude_tool_usage and exclude_reasoning parameters control output."""
    result = message_as_str(
        message,
        ContentFilter(
            exclude_tool_usage=exclude_tool_usage, exclude_reasoning=exclude_reasoning
        ),
    )
    assert result == expected


@pytest.mark.parametrize(
    "messages,filter,include_ids,expected_result,expected_ids",
    [
        # Basic case without IDs
        (
            [
                ChatMessageUser(content="Hello", id="msg1"),
                ChatMessageAssistant(content="Hi", id="msg2"),
            ],
            None,
            False,
            "user:\nHello\n\nassistant:\nHi\n",
            None,
        ),
        # Basic case with IDs
        (
            [
                ChatMessageUser(content="Hello", id="msg1"),
                ChatMessageAssistant(content="Hi", id="msg2"),
            ],
            None,
            True,
            "[M1] user:\nHello\n\n[M2] assistant:\nHi\n",
            {"M1": "msg1", "M2": "msg2"},
        ),
        # System messages excluded by default
        (
            [
                ChatMessageSystem(content="System", id="sys1"),
                ChatMessageUser(content="Hello", id="msg1"),
            ],
            ContentFilter(),
            True,
            "[M1] user:\nHello\n",
            {"M1": "msg1"},
        ),
        # Tool messages excluded when filter set
        (
            [
                ChatMessageUser(content="Hello", id="msg1"),
                ChatMessageTool(content="Tool result", function="test", id="tool1"),
                ChatMessageAssistant(content="Done", id="msg2"),
            ],
            ContentFilter(exclude_tool_usage=True),
            True,
            "[M1] user:\nHello\n\n[M2] assistant:\nDone\n",
            {"M1": "msg1", "M2": "msg2"},
        ),
        # Empty list
        ([], None, True, "", {}),
        # Single message
        (
            [ChatMessageUser(content="Single", id="msg1")],
            None,
            True,
            "[M1] user:\nSingle\n",
            {"M1": "msg1"},
        ),
    ],
)
@pytest.mark.asyncio
async def test_messages_as_str(
    messages: list[ChatMessage],
    filter: ContentFilter | None,
    include_ids: bool,
    expected_result: str,
    expected_ids: dict[str, str] | None,
) -> None:
    """Test messages_as_str with various configurations."""
    if include_ids:
        result, message_ids = await messages_as_str(
            messages, content_filter=filter, include_ids=True
        )
        assert result == expected_result
        assert message_ids == expected_ids
    else:
        result = await messages_as_str(messages, content_filter=filter)
        assert result == expected_result


@pytest.mark.asyncio
async def test_messages_as_str_with_preprocessor() -> None:
    """Test messages_as_str with async message preprocessor."""

    async def keep_only_user_messages(
        messages: list[ChatMessage],
    ) -> list[ChatMessage]:
        return [m for m in messages if m.role == "user"]

    messages: list[ChatMessage] = [
        ChatMessageUser(content="User 1", id="msg1"),
        ChatMessageAssistant(content="Assistant 1", id="msg2"),
        ChatMessageUser(content="User 2", id="msg3"),
    ]

    result, message_ids = await messages_as_str(
        messages,
        content_filter=ContentFilter(messages=keep_only_user_messages),
        include_ids=True,
    )

    assert message_ids == {"M1": "msg1", "M2": "msg3"}
    assert "[M1] user:\nUser 1\n" in result
    assert "[M2] user:\nUser 2\n" in result
    assert "Assistant" not in result
