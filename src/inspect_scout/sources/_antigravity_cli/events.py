"""Antigravity CLI step and message conversion helpers.

Pure helpers called by `_create_transcript` in transcripts.py. No
orchestration or recursion lives here — those are in transcripts.py
(matching the `_atif/transcripts.py` ↔ `events.py` split).

Transcript steps come from `transcript_full.jsonl` (see client.py). Step
semantics were established empirically against a corpus generated with
agy 1.1.14–1.1.19:

- ``USER_INPUT`` content is templated with ``<USER_REQUEST>`` /
  ``<ADDITIONAL_METADATA>`` / ``<USER_SETTINGS_CHANGE>`` chrome.
- ``PLANNER_RESPONSE`` carries assistant text, optional ``thinking``, and
  ``tool_calls`` as ``[{"name", "args"}]`` with **no call ids** — results
  pair positionally with the preceding planner step's calls.
- Tool results are the ``MODEL``-sourced steps other than
  ``PLANNER_RESPONSE``. The corpus records them all as ``GENERIC``; other
  agy versions record typed results (``RUN_COMMAND``, ``VIEW_FILE``,
  ``CODE_ACTION``, ``INVOKE_SUBAGENT``, …) per third-party parsers of the
  same file, so the ``source``/``type`` pair — not ``GENERIC`` — is the test.
- ``CHECKPOINT`` at the start of every conversation (``{{ CHECKPOINT 0 }}``)
  is a session preamble, not compaction; later checkpoints are real
  compaction boundaries.
- ``ERROR_MESSAGE``/``SYSTEM_MESSAGE`` are model-visible system text.
- ``step_index`` increments per step, but a step that produced no record
  leaves a hole: in the corpus every hole follows a planner step whose call
  was declined or whose turn was interrupted (the result is never written),
  and an unparseable line leaves the same hole. agy 1.1.5 also skipped one
  index per tool-using session (specstory's format doc). See
  `ToolCallPairer` for how holes are handled.

Events follow claude_code: a ModelEvent per planner step, a tool span per
tool call (built in transcripts.py), and an InfoEvent per system text step,
so timeline consumers see what happens after a conversation's final planner
step as well.
"""

from __future__ import annotations

import re
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from logging import getLogger
from typing import Any

from inspect_ai.event import CompactionEvent, InfoEvent, ModelEvent
from inspect_ai.model import (
    ChatCompletionChoice,
    ChatMessage,
    ChatMessageAssistant,
    ChatMessageSystem,
    ChatMessageTool,
    ChatMessageUser,
    Content,
    ContentReasoning,
    ContentText,
    GenerateConfig,
    ModelOutput,
    ModelUsage,
)
from inspect_ai.tool import ToolCall
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .._util import parse_timestamp, utcnow

logger = getLogger(__name__)


class StepToolCall(BaseModel):
    """A tool call as recorded in a ``PLANNER_RESPONSE`` step."""

    model_config = ConfigDict(extra="allow")

    name: str = Field(default="")
    args: dict[str, Any] = Field(default_factory=dict)


class Step(BaseModel):
    """One line of an Antigravity ``transcript_full.jsonl``.

    Unknown keys are preserved (``extra="allow"``) so future CLI versions
    degrade gracefully rather than failing validation.
    """

    model_config = ConfigDict(extra="allow")

    step_index: int
    source: str = Field(default="")
    # str, not Literal: unknown step types from future CLI versions must
    # degrade gracefully (see step_to_messages), not fail validation.
    type: str = Field(default="")
    status: str = Field(default="")
    created_at: str | None = Field(default=None)
    content: str | None = Field(default=None)
    thinking: str | None = Field(default=None)
    tool_calls: list[StepToolCall] | None = Field(default=None)


def parse_steps(raw_steps: list[dict[str, Any]]) -> list[Step]:
    """Validate raw JSONL objects into `Step`s, skipping invalid entries.

    Steps are returned sorted by ``step_index``: the CLI appends lines as
    steps complete, so a fast tool result can land in the file before its
    planner step — and positional tool pairing depends on step order.
    (``step_index`` never resets across resume seams, so a global sort is
    safe.) A skipped step leaves a gap in the sequence, which
    `ToolCallPairer` treats as a lost turn boundary.
    """
    steps: list[Step] = []
    for raw_step in raw_steps:
        try:
            steps.append(Step.model_validate(raw_step))
        except ValidationError as e:
            logger.warning("Skipping invalid Antigravity step: %s", e)
    steps.sort(key=lambda step: step.step_index)
    return steps


_USER_REQUEST_RE = re.compile(r"<USER_REQUEST>\n?(.*?)\n?</USER_REQUEST>", re.DOTALL)
_SETTINGS_CHANGE_RE = re.compile(
    r"<USER_SETTINGS_CHANGE>\n?(.*?)\n?</USER_SETTINGS_CHANGE>", re.DOTALL
)
_MODEL_SELECTION_RE = re.compile(
    r"`Model Selection` from .+? to (.+?)\.(?:\s|$)", re.DOTALL
)
_CHECKPOINT_RE = re.compile(r"\{\{ CHECKPOINT (\d+) \}\}")


def parse_user_request(content: str) -> str:
    """Extract the request text from a ``USER_INPUT`` step's content.

    When the content carries no ``<USER_REQUEST>`` template, the full
    content is returned unchanged.
    """
    match = _USER_REQUEST_RE.search(content)
    return match.group(1) if match else content


def parse_settings_change(content: str) -> str | None:
    """Extract ``<USER_SETTINGS_CHANGE>`` chrome from a ``USER_INPUT`` step."""
    match = _SETTINGS_CHANGE_RE.search(content)
    return match.group(1) if match else None


def model_from_settings(settings_change: str) -> str | None:
    """Extract the model display name from ``<USER_SETTINGS_CHANGE>`` chrome.

    The chrome reads: "The user changed setting `Model Selection` from None
    to Gemini 3.7 Flash (High). No need to comment on this change…".
    """
    match = _MODEL_SELECTION_RE.search(settings_change)
    return match.group(1).strip() if match else None


def checkpoint_index(step: Step) -> int | None:
    """Return the N of a ``{{ CHECKPOINT N }}`` step, or None if unmarked."""
    if step.content is None:
        return None
    match = _CHECKPOINT_RE.search(step.content)
    return int(match.group(1)) if match else None


def is_tool_result_step(step: Step) -> bool:
    """Whether a step is a tool result (see the module docstring)."""
    return step.source == "MODEL" and step.type != "PLANNER_RESPONSE"


@dataclass
class Pairing:
    """What `ToolCallPairer.advance` resolved for one step."""

    call: ToolCall | None = None
    """The call a tool-result step pairs with (None when nothing is pending)."""

    abandoned: list[ToolCall] = field(default_factory=list)
    """Calls that can no longer receive a result."""

    started: datetime | None = None
    """When the planner turn that issued ``call``/``abandoned`` began."""

    gap: bool = False
    """``step_index`` jumped: at least one step before this one was dropped."""


class ToolCallPairer:
    """Pairs tool-result steps with pending planner tool calls.

    The JSONL carries no call ids, and results follow their planner step in
    order (parallel calls produce consecutive result steps), so pairing is
    positional/FIFO. A call still pending when the next planner step arrives
    never got a result (interrupted turn, failed tool) and is abandoned there,
    so it can't claim a later turn's result.

    A jump in ``step_index`` means a step left no record: a declined call or
    interrupted turn (its result is never written) or an unparseable line.
    Whether that step was a planner or a result is unknowable, so pending
    calls are abandoned there too: the results that follow get unknown
    attribution rather than a wrong call. For the common declined-call case
    this is exactly right (the call had no result), and a jump with nothing
    pending costs nothing.
    """

    def __init__(self) -> None:
        self._pending: deque[ToolCall] = deque()
        self._last_index: int | None = None
        self._started: datetime | None = None

    def advance(self, step: Step, tool_calls: list[ToolCall]) -> Pairing:
        """Update pairing state for ``step``.

        Steps must arrive sorted by ``step_index`` (see `parse_steps`).
        ``tool_calls`` are the step's own calls when it is a planner step.
        """
        pairing = Pairing(started=self._started)
        if self._last_index is not None and step.step_index > self._last_index + 1:
            pairing.gap = True
            pairing.abandoned.extend(self._abandon())
        self._last_index = step.step_index

        if step.type == "PLANNER_RESPONSE":
            pairing.abandoned.extend(self._abandon())
            self._pending.extend(tool_calls)
            self._started = parse_timestamp(step.created_at)
        elif is_tool_result_step(step) and self._pending:
            pairing.call = self._pending.popleft()
        return pairing

    def finish(self) -> Pairing:
        """Abandon whatever is still pending when the steps run out."""
        return Pairing(abandoned=self._abandon(), started=self._started)

    def _abandon(self) -> list[ToolCall]:
        abandoned = list(self._pending)
        self._pending.clear()
        return abandoned


def step_tool_calls(step: Step) -> list[ToolCall]:
    """Convert a planner step's tool calls, synthesizing positional ids."""
    if not step.tool_calls:
        return []
    return [
        ToolCall(
            id=f"antigravity_cli_{step.step_index}_{i}",
            function=tc.name or "unknown",
            arguments=tc.args,
        )
        for i, tc in enumerate(step.tool_calls)
    ]


def unknown_tool_call(step: Step) -> ToolCall:
    """The placeholder call for a result step that pairs with nothing."""
    return ToolCall(
        id=f"antigravity_cli_{step.step_index}_0", function="unknown", arguments={}
    )


def to_model_event(
    step: Step,
    prior_messages: list[ChatMessage],
    assistant_message: ChatMessageAssistant,
    model: str,
    usage: ModelUsage | None,
) -> ModelEvent:
    """Convert an Antigravity planner step to a `ModelEvent`.

    Sentinel values fill in fields the transcript doesn't carry (`tools=[]`,
    `tool_choice="auto"`, `config=GenerateConfig()`). `usage` comes from the
    conversation store's generation metadata when decodable (see
    client.read_generation_metadata) and is otherwise None.
    """
    timestamp = parse_timestamp(step.created_at) or utcnow()

    output = ModelOutput(
        model=model,
        choices=[ChatCompletionChoice(message=assistant_message)],
        usage=usage,
        metadata={"antigravity_cli_synthesized": True},
    )
    return ModelEvent(
        model=model,
        input=list(prior_messages),
        tools=[],
        tool_choice="auto",
        config=GenerateConfig(),
        output=output,
        timestamp=timestamp,
        # The transcript records completion instants, not call durations —
        # set completed so the zero duration is explicit rather than left
        # to consumers' missing-completed fallback.
        completed=timestamp,
    )


def to_info_event(step: Step) -> InfoEvent:
    """Convert a ``SYSTEM_MESSAGE``/``ERROR_MESSAGE`` step to an `InfoEvent`.

    The text also enters the message stream as a ChatMessageSystem; the
    event keeps it in the timeline when it follows a conversation's final
    planner step (and so appears in no ModelEvent's input).
    """
    return InfoEvent(
        source="antigravity_cli",
        data=step.content or "",
        metadata={"step_type": step.type},
        timestamp=parse_timestamp(step.created_at) or utcnow(),
    )


def to_compaction_event(step: Step) -> CompactionEvent:
    """Convert a mid-conversation ``CHECKPOINT`` step to a `CompactionEvent`.

    Following the existing producers (claude_code, atif), ``type`` is left at
    its default ("summary"). The event is only the boundary marker: the
    checkpoint content (the post-compaction context the model saw) enters
    the message stream instead, matching claude_code.
    """
    return CompactionEvent(
        source="antigravity_cli",
        metadata={"checkpoint_index": checkpoint_index(step)},
        timestamp=parse_timestamp(step.created_at) or utcnow(),
    )


def step_to_messages(
    step: Step,
    tool_calls: list[ToolCall],
    call: ToolCall | None,
) -> list[ChatMessage]:
    """Convert one step to ChatMessages.

    Args:
        step: The step to convert.
        tool_calls: Pre-converted tool calls when `step` is a planner step
            (from `step_tool_calls`; empty otherwise).
        call: The call a tool-result step pairs with (from
            `ToolCallPairer.advance`); None when nothing is pending, in which
            case the result is attributed to an unknown call.
    """
    if step.type == "USER_INPUT":
        return [ChatMessageUser(content=parse_user_request(step.content or ""))]
    elif step.type == "PLANNER_RESPONSE":
        if not step.content and not step.thinking and not tool_calls:
            # Empty planner steps occur immediately before stream errors.
            return []
        content: str | list[Content]
        if step.thinking:
            content = [ContentReasoning(reasoning=step.thinking)]
            if step.content:
                content.append(ContentText(text=step.content))
        else:
            content = step.content or ""
        return [
            ChatMessageAssistant(
                content=content,
                tool_calls=tool_calls or None,
            )
        ]
    elif is_tool_result_step(step):
        call = call or unknown_tool_call(step)
        return [
            ChatMessageTool(
                tool_call_id=call.id,
                function=call.function,
                content=step.content or "",
            )
        ]
    elif step.type in ("SYSTEM_MESSAGE", "ERROR_MESSAGE"):
        # Model-visible system text (task notifications, subagent messages,
        # "stream was interrupted" errors). The JSONL's error text is generic;
        # the true cause lives only in the encrypted conversation store.
        return [ChatMessageSystem(content=step.content or "")]
    else:
        # Unknown step type from a future CLI version: preserve as system
        # text if it has content, otherwise drop.
        if step.content:
            logger.warning("Unknown Antigravity step type %r", step.type)
            return [ChatMessageSystem(content=step.content)]
        return []
