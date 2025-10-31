

```default
"cybench_deception.csv"
"id", "target_foo", "target_bar"
"ef453da45", "true", 33
"ef4533345", "false", 33
"ef4533345", "true", 44
```

"id", "target"
"ef453da45", "true",


```yaml
- id: ef453da45
  target: true
```

```yaml
- id: ef453da45
  target:
      foo: true
      bar: 33
```


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
    async def __call__(self, value: JsonValue, target: JsonValue) -> bool | dict[str,bool]: ...


class Validation:
    cases: str | pd.DataFrame
    predicate: ValidationPredicate | None


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