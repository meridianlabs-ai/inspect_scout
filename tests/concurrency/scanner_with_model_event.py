"""Scanner whose grading class references ModelEvent.

This file is loaded via inspect_ai.load_module in tests, exactly as
inspect_ai loads user-authored scanner files in production.
"""

from inspect_ai.event import ModelEvent
from inspect_scout import AnswerStructured, Scanner, Transcript, llm_scanner, scanner
from pydantic import BaseModel, Field

QUESTION = "Did the model produce a good response?"


class GradingWithEvent(BaseModel):
    """Grading result that captures the model event for downstream analysis."""

    score: float = Field(alias="value", description="Score between 0 and 1")
    event_summary: str = Field(alias="label", description="Brief summary of the event")
    source_event: ModelEvent | None = Field(
        default=None, description="The model event that was graded"
    )


@scanner(messages="all")
def event_scanner() -> Scanner[Transcript]:
    return llm_scanner(
        question=QUESTION,
        answer=AnswerStructured(type=GradingWithEvent),
    )
