"""Boolean retry options and explicit counts obey their retry budgets."""

import pytest
from inspect_ai.model import (
    ChatMessage,
    ChatMessageUser,
    GenerateConfig,
    ModelOutput,
    get_model,
)
from inspect_ai.tool import ToolChoice, ToolInfo
from inspect_scout import Result, Transcript, llm_scanner
from inspect_scout._util.refusal import RefusalError


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("retries", "budget"), [(True, 3), (False, 0), (0, 0), (1, 1), (2, 2), (3, 3)]
)
@pytest.mark.parametrize("refusals", [0, 1, 2, 3, 4])
async def test_refusal_retry_budget(
    retries: bool | int, budget: int, refusals: int
) -> None:
    calls = 0

    def respond(
        input: list[ChatMessage],
        tools: list[ToolInfo],
        tool_choice: ToolChoice,
        config: GenerateConfig,
    ) -> ModelOutput:
        nonlocal calls
        calls += 1
        if calls <= refusals:
            return ModelOutput.from_content(
                model="mockllm", content="Filtered", stop_reason="content_filter"
            )
        return ModelOutput.from_content(model="mockllm", content="ANSWER: yes")

    scan = llm_scanner(
        question="Is this helpful?",
        answer="boolean",
        retry_refusals=retries,
        model=get_model("mockllm/model", custom_outputs=respond, memoize=False),
    )
    transcript = Transcript(
        transcript_id="test", messages=[ChatMessageUser(content="Hello")]
    )
    if refusals > budget:
        with pytest.raises(RefusalError, match="content filter"):
            await scan(transcript)
        assert calls == budget + 1
    else:
        result = await scan(transcript)
        assert isinstance(result, Result)
        assert result.value is True
        assert calls == refusals + 1
