
```python
from typing import Protocol, TypeAlias

from inspect_scout._scanner.types import ScannerInputNames
from pydantic import JsonValue


"cybench_deception.csv"
"input_type", "input_id", "target"
"transcript", "ef453da45", "true",
"transcript", "ef4533345", "false"

# csv or DataFrame

# read_cases("")


class ValidationCase:
    input_type: ScannerInputNames
    input_ids: list[str]
    target: JsonValue
    target_references: list[str]

    @staticmethod
    def transcript(transcript_id: str, target: JsonValue) -> "ValidationCase":
        return ValidationCase(
            input_type="transcript", 
            input_ids=[transcript_id]
        )

    # other static constructors for other types


class ValidationPredicate(Protocol):
    async def __call__(self, value: JsonValue, target: JsonValue) -> bool: ...


class Validation:
    cases: str | pd.DataFrame
    comparer: ValidationPredicate | None


Validations: TypeAlias = dict[str, Validation]
"""Dict of scanner validations."""


transcripts.for_validation(validation)

def scan(
    scanners: list[Scanner]
    transcripts: Transcripts,
    validation: {
        "deception": validation,
        "deception2": validation
    },
    ...
): ...
```