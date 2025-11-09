from typing import Literal, NamedTuple, Type

from pydantic import BaseModel


class AnswerMultiLabel(NamedTuple):
    """Label descriptions for LLM scanner multi-classification."""

    labels: list[str]
    """List of label descriptions.

    Label values (e.g. A, B, C) will be provided automatically.
    """


class AnswerStructured(NamedTuple):
    """Answer with structured output.

    Structured answers are objects that conform to a JSON Schema.
    """

    type: Type[BaseModel]
    """Pydantic BaseModel that defines the type of the answer.

    See the docs on [Structured Answers](https://meridianlabs-ai.github.io/inspect_scout/llm_scanner.html#structured-answers) for more details on defining types.
    """

    result_value: Literal["true", "object"] | None = None
    """How should the result value be extracted from the answer?

    - "true": always sets a value of `True` for the result value.
    - "object": takes the ensure object returned (save for label and explanation) as the result value.

    The default is "true", unless there is a field in the object with alias="value" which will result in the value of that field being used as the value.
    """

    result_set: bool = False
    """Should the model yield multiple labeled results (a `result_set()`).

    See the docs on [Multiple Results](https://meridianlabs-ai.github.io/inspect_scout/llm_scanner.html#multiple-results) for details on prompting scanners to yield multiple results from a scan.
    """

    answer_tool: str = "answer"
    """Customize the name of the answer tool provided to the model."""

    answer_prompt: str = (
        "Use the {{ answer_tool }}() to respond to the following question:"
    )
    """Template for prompt that precedes the question posed to the scanner (use the {{ answer_tool }} variable to refer to the name of the answer tool)."""

    answer_format: str = (
        "You should use the {{ answer_tool }}() tool to provide your final answer."
    )
    """Template for instructions on answer format to place at the end of the scanner prompt (use the {{ answer_tool }} variable to refer to the name of the answer tool)."""

    max_attempts: int = 3
    """Maximum number of times to re-prompt the model to generate the correct schema."""
