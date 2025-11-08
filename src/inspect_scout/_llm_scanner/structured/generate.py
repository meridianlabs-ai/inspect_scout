from typing import Any, NamedTuple

from inspect_ai.model import (
    ChatMessage,
    ChatMessageTool,
    Model,
    ModelOutput,
    execute_tools,
    get_model,
)
from inspect_ai.tool import ToolDef, ToolFunction, ToolParams
from inspect_ai.util import JSONSchema
from pydantic import JsonValue


class StructuredGenerate(NamedTuple):
    value: dict[str, JsonValue] | None
    """Structured value yielded by generation."""

    messages: list[ChatMessage]
    """Additional messages yielded by generation"""

    output: ModelOutput
    """Final model output from generation."""


class AnswerTool(NamedTuple):
    name: str = "answer"
    description: str = "Use this tool to submit your final answer."


async def structured_generate(
    input: list[ChatMessage],
    schema: JSONSchema,
    model: str | Model | None = None,
    answer_tool: AnswerTool | None = None,
    max_attempts: int = 3,
) -> StructuredGenerate:
    # resolve model and answer tool
    model = get_model(model)
    answer_tool = answer_tool or AnswerTool()

    # create a dynamic tool definition for the answer tool
    async def answer(**kwargs: Any) -> str:
        return ""

    answer_tooldef = ToolDef(
        tool=answer,
        name=answer_tool.name,
        description=answer_tool.description,
        parameters=ToolParams(
            type="object",
            properties=schema.properties or {},
            required=schema.required or [],
        ),
    )

    # setup initial values for messages and output (we will return these)
    value: dict[str, JsonValue] | None = None
    messages = input.copy()
    output: ModelOutput

    # setup a generate loop that will run until a successful call to the
    # anwser tool is made
    attempts = 0
    while attempts < max_attempts:
        output = await model.generate(
            input=messages,
            tools=[answer_tooldef],
            tool_choice=ToolFunction(answer_tooldef.name),
        )
        messages.append(output.message)

        # check for a call to the 'answer' tool
        answer_tool_call = next(
            (
                tool_call
                for tool_call in (output.message.tool_calls or [])
                if tool_call.function == answer_tool.name
            ),
            None,
        )
        if answer_tool_call:
            # execute the tool calls (this will take care of validating the
            # answer tool parameters and providing feedback for invalid cases)
            execute_messages, execute_output = await execute_tools(
                messages=messages, tools=[answer_tooldef]
            )
            messages.extend(execute_messages)
            if execute_output is not None:
                output = execute_output

            # exit if there was a successful call of the answer tool
            if isinstance(messages[-1], ChatMessageTool):
                tool_message = messages[-1]
                if tool_message.error is None:
                    value = answer_tool_call.arguments
                    break

        # keep going
        attempts += 1

    # return result
    return StructuredGenerate(value=value, messages=messages, output=output)
