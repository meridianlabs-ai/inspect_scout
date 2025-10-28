from dataclasses import dataclass
from typing import Literal


@dataclass
class Preprocessor:
    exclude_system: bool = True
    exclude_reasoning: bool = False
    exclude_tool_usage: bool = False


@dataclass
class AnswerType:
    type: Literal[
        # rate on 1-10, xxx
        "number",
        # yes/no
        "bool",
        # list discussed celebrities by name
        "str",
        # A,B,C,D
        "label",
        # Which of the categories defined above are xxx
        "labels",
    ]
    labels: list[str] | None = None
    multi_classification: bool = False
