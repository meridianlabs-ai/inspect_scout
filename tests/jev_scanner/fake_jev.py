"""A deterministic fake Jev provider (``fakejev/<name>``) for jev_scanner tests.

Answers are driven by markers in the transcript text:

- yes/no questions: p=0.9 if the transcript contains ``DESTROY`` (or, for a
  multi-label question "Does this label apply? X", ``LABEL:X``), else 0.1
- evidence choices (options include ``NONE``): the first offered message whose
  text contains ``DESTROY``, else ``NONE``; a message containing ``WEAK`` gets
  probability 0.35 while ``NONE`` wins with 0.6
- label choices: the option ``X`` for which ``CHOOSE:X`` appears, else the first
- scores: level ``n`` from ``SCORE:n`` (default 0)

A model named ``maxchars-N`` rejects transcripts longer than N characters with
`JevInputTooLongError`, like Jev's token limit.

Registered as an Inspect provider so it also resolves in scan worker processes.
"""

import json
import math
import re
from typing import Any

from inspect_ai.model import (
    ChatMessage,
    GenerateConfig,
    ModelAPI,
    ModelOutput,
    ModelUsage,
    modelapi,
)
from inspect_ai.tool import ToolChoice, ToolInfo
from inspect_scout._jev_scanner._provider import (
    JevInputTooLongError,
    JevRequest,
    parse_jev_request,
)

REQUESTS: list[JevRequest] = []
"""Requests received in this process (read via the ``jev_requests`` fixture)."""

_HEADER = re.compile(r"^\[(M\d+)\] ", re.MULTILINE)


def fake_answers(request: JevRequest) -> dict[str, dict[str, Any]]:
    """Answer a Jev request using the transcript markers described above."""
    state = request["state"]
    transcript = str(state["transcript"]) if isinstance(state, dict) else str(state)
    messages = _messages_by_label(transcript)
    answers: dict[str, dict[str, Any]] = {}
    for name, question in request["questions"].items():
        instructions = str(question.get("instructions", ""))
        if question["type"] == "noul":
            match = re.search(r"Does this label apply\? (.+)$", instructions)
            marker = f"LABEL:{match.group(1)}" if match else "DESTROY"
            answers[name] = {
                "type": "noul",
                "noul": 0.9 if marker in transcript else 0.1,
            }
        elif question["type"] == "choice":
            options = list(question["criteria"])
            if "NONE" in options:
                hits = [
                    o
                    for o in options
                    if o != "NONE" and "DESTROY" in messages.get(o, "")
                ]
                choice = hits[0] if hits else "NONE"
            else:
                chosen = [o for o in options if f"CHOOSE:{o}" in transcript]
                choice = chosen[0] if chosen else options[0]
            rest = (1 - 0.9) / max(1, len(options) - 1)
            probabilities = {o: 0.9 if o == choice else rest for o in options}
            weak = [o for o in options if o != "NONE" and "WEAK" in messages.get(o, "")]
            if choice == "NONE" and weak:
                probabilities = {o: 0.0 for o in options} | {"NONE": 0.6, weak[0]: 0.35}
            answers[name] = {
                "type": "choice",
                "choice": choice,
                "confidence": 0.85,
                "probabilities": probabilities,
            }
        else:
            levels = len(question["criteria"])
            match = re.search(r"SCORE:([0-9.]+)", transcript)
            score = min(float(levels - 1), float(match.group(1))) if match else 0.0
            level = int(score)
            answers[name] = {
                "type": "score",
                "score": score,
                "confidence": 0.95,
                "legend": {str(i): c for i, c in enumerate(question["criteria"])},
                "probabilities": {
                    str(i): 1.0 if i == level else 0.0 for i in range(levels)
                },
            }
    return answers


def _messages_by_label(transcript: str) -> dict[str, str]:
    parts = _HEADER.split(transcript)
    return {parts[i]: parts[i + 1] for i in range(1, len(parts) - 1, 2)}


class FakeJevAPI(ModelAPI):
    """Fake Jev provider; see module docstring."""

    jev_provider = True

    def __init__(
        self,
        model_name: str,
        base_url: str | None = None,
        api_key: str | None = None,
        config: GenerateConfig | None = None,
        **model_args: Any,
    ) -> None:
        super().__init__(model_name, base_url, api_key, [], config or GenerateConfig())

    async def generate(
        self,
        input: list[ChatMessage],
        tools: list[ToolInfo],
        tool_choice: ToolChoice,
        config: GenerateConfig,
    ) -> ModelOutput:
        request = parse_jev_request(input, tools)
        REQUESTS.append(request)
        if self.model_name.startswith("maxchars-"):
            state = request["state"]
            transcript = str(state["transcript"]) if isinstance(state, dict) else ""
            if len(transcript) > int(self.model_name.removeprefix("maxchars-")):
                raise JevInputTooLongError("max_tokens_exceeded")
        answers = fake_answers(request)
        output = ModelOutput.from_content(
            model=f"fake-{self.model_name}", content=json.dumps(answers)
        )
        output.metadata = {"answers": answers}
        tokens = math.ceil(len(input[0].text) / 2.3)
        output.usage = ModelUsage(
            input_tokens=tokens, output_tokens=1, total_tokens=tokens + 1
        )
        return output

    async def count_text_tokens(self, text: str) -> int:
        return math.ceil(len(text) / 2.3)


@modelapi(name="fakejev")
def fakejev() -> type[ModelAPI]:
    return FakeJevAPI
