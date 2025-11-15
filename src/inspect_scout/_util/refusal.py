from typing import Sequence

from inspect_ai.model import ChatMessage, GenerateConfig, Model, ModelOutput
from inspect_ai.tool import Tool, ToolChoice, ToolDef, ToolInfo, ToolSource


class RefusalError(RuntimeError):
    """Error indicating that the model refused a scan request."""

    pass


async def generate_retry_refusals(
    model: Model,
    input: str | list[ChatMessage],
    tools: Sequence[Tool | ToolDef | ToolInfo | ToolSource] | ToolSource,
    tool_choice: ToolChoice | None,
    config: GenerateConfig | None,
    retry_refusals: int,
) -> ModelOutput:
    refusals = 0
    while True:
        # run the generation
        output = await model.generate(
            input=input,
            tool_choice=tool_choice,
            tools=tools,
            config=config or GenerateConfig(),
        )

        # check for refusal and retry if needed (else raise error)
        if output.stop_reason == "content_filter":
            if refusals < retry_refusals:
                refusals += 1
            else:
                raise RefusalError(
                    f"Scanner request refused by content filter: {output.completion}"
                )
        else:
            return output
