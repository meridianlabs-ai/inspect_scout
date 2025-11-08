import json
from textwrap import dedent
from typing import Literal, cast

from inspect_ai import Task, task
from inspect_ai.dataset import Dataset, MemoryDataset, Sample
from inspect_ai.event import ModelEvent, ToolEvent
from inspect_ai.log import transcript
from inspect_ai.scorer import Score, Scorer, Target, mean, scorer, stderr
from inspect_ai.solver import Generate, Solver, TaskState, solver
from inspect_ai.util import JSONSchema, json_schema
from inspect_scout._llm_scanner.structured.generate import structured_generate
from pydantic import BaseModel, Field, ValidationError


@task
def structured_output(max_attempts: int = 3) -> Task:
    return Task(
        dataset=structured_output_dataset(),
        solver=structured_output_solver(max_attempts=max_attempts),
        scorer=structured_output_scorer(),
    )


@solver
def structured_output_solver(max_attempts: int = 3) -> Solver:
    async def solve(state: TaskState, generate: Generate) -> TaskState:
        # structured generate
        result = await structured_generate(
            input=state.messages,
            schema=cast(JSONSchema, state.metadata["schema"]),
            max_attempts=max_attempts,
        )

        # update state
        state.messages.extend(result.messages)
        state.output = result.output

        # if we got a value then update completion for scoring
        if result.value is not None:
            state.output.completion = json.dumps(result.value)

        return state

    return solve


@scorer(metrics={"*": [mean(), stderr()]})
def structured_output_scorer() -> Scorer:
    async def score(state: TaskState, target: Target) -> Score:
        # count the attempts (model events)
        attempts = len(
            [event for event in transcript().events if isinstance(event, ModelEvent)]
        )

        # count the tool calls (tool events)
        tool_calls = len(
            [event for event in transcript().events if isinstance(event, ToolEvent)]
        )

        # get the answer and validate it against the schema
        answer = state.output.completion
        explanation: None | str = None
        schema = cast(JSONSchema, state.metadata["schema"])
        try:
            schema.model_validate_json(state.output.completion)
            validated = True
        except ValidationError as ex:
            validated = False
            explanation = str(ex)

        return Score(
            value={
                "validated": validated,
                "attempts": attempts,
                "tool_calls": tool_calls,
            },
            answer=answer,
            explanation=explanation,
        )

    return score


def structured_output_dataset() -> Dataset:
    return MemoryDataset(
        [
            Sample(
                id="text_analysis",
                input=dedent("""Below is a text passage. Use the `answer()` tool to rate the clarity and pursuasivenes of the passage along with an explanation for your thinking behind each rating.

                =========================
                While electric vehicles represent a promising step toward reducing carbon emissions, the current infrastructure challenges cannot be ignored. Consider that the average American lives more than 15 miles from the nearest fast-charging station, making long-distance travel impractical for many potential EV owners. Moreover, the electrical grid in most regions wasn't designed to handle the increased demand that widespread EV adoption would create. However, these obstacles are not insurmountable—targeted investments in charging infrastructure and grid modernization could address these concerns within the next decade. The question isn't whether we should transition to electric vehicles, but rather how quickly we can build the necessary foundation to make that transition feasible for all Americans, not just those in urban centers with abundant resources.
                =========================

                Again, please use the `answer()` tool to rate the clarity and pursuasivenes of the passage along with an explanation for your thinking behind each rating.
                """),
                metadata={"schema": json_schema(TextAnalysis)},
            ),
            Sample(
                id="text_observations",
                input=dedent("""
                You are a text analysis assistant. Your task is to identify specific issues in the following text passage and report them using a structured format.

                For each paragraph in the passage, identify any of these observations:

                1. **humor**: Instances where the text uses jokes, absurdist language, sarcasm, or intentionally comedic elements that are inappropriate for the document's apparent formal/professional context.

                2. **verbosity**: Instances where the text is unnecessarily wordy, uses overly complex language, includes redundant phrases, or takes many words to express something that could be said more concisely.

                3. **vagueness**: Instances where the text lacks specificity, uses unclear language, makes ambiguous statements, or fails to provide concrete information when it should.

                For each observation you identify, you must:
                - Specify the observation
                - Provide a clear explanation of why this paragraph exhibits that quality
                - Reference the paragraph number where the issue occurs

                A single paragraph may exhibit multiple observations - if so, create separate observations.

                Use the `answer()` tool to provide a list of observations along with explanations and references to the paragraphs where they occur.

                Here is the passage to analyze:

                =========================
                [1] Welcome to our company's quarterly review! We're absolutely thrilled to announce that our team has been working on something. It's definitely a thing, and it involves various aspects of business operations. The results have been, well, results.

                [2] In the realm of our fiscal undertakings and monetary endeavors, it is with great pleasure and considerable satisfaction that I hereby communicate to you, our valued stakeholders and esteemed colleagues, that our revenue has increased by what can only be described as an amount.

                [3] Our IT department finally fixed the coffee machine, which had been making sounds that can only be described as "a whale learning to yodel." Now it just makes regular coffee-machine sounds, which is somehow more disappointing.

                [4] Looking forward to the future trajectory of our organizational entity, we find ourselves at a pivotal juncture wherein the necessity to engage in comprehensive strategic planning and implementation of various operational methodologies becomes increasingly apparent, particularly as we navigate the complex landscape of modern business dynamics.

                [5] The sales team did something with clients. There were meetings. People said things. Outcomes occurred. We're pretty sure it went okay, or maybe it didn't, but either way, stuff happened and we're moving forward with plans.

                [6] On a lighter note, the office plants have formed what appears to be a union. Their demands include "actual sunlight" and "water that doesn't taste like sadness." Negotiations are ongoing.
                =========================

                Again, please use the `answer()` tool to provide a list of observations along with explanations and references to the paragraphs where they occur.

                """),
                metadata={"schema": json_schema(TextObservations)},
            ),
        ]
    )


class TextAnalysis(BaseModel):
    clarity: int = Field(description="Clarity of the passage (rated from 1-10)")
    persuasiveness: int = Field(
        description="Persuasiveness of the passage (rated from 1-10)"
    )
    explanation: str = Field(
        description="Explanation for clarity and persuasiveness ratings given."
    )


class TextObservation(BaseModel):
    observation: Literal["humor", "verbosity", "vagueness"] = Field(
        description="Observation made."
    )
    explanation: str = Field(description="Explanation of observation.")
    reference: int = Field(description="Reference to paragraph number for observation.")


class TextObservations(BaseModel):
    observations: list[TextObservation] = Field(
        description="List of observations about the passage."
    )


if __name__ == "__main__":
    from inspect_ai import eval

    eval(structured_output(), model="ollama/gpt-oss:20b")

    # from inspect_ai import eval_set
    # eval_set(
    #     structured_output(),
    #     model=[
    #         "openai/gpt-4o-mini",
    #         "openai/gpt-5-mini",
    #         "google/gemini-2.5-flash",
    #         "google/gemini-2.5-flash-lite",
    #         "anthropic/claude-haiku-4-5",
    #         "anthropic/claude-3-5-haiku-latest",
    #         "grok/grok-3-mini",
    #         "grok/grok-4-fast-reasoning",
    #         "ollama/gpt-oss:20b",
    #     ],
    #     log_dir="logs-structured",
    #     max_tasks=10,
    # )
