from inspect_ai import Task, eval
from inspect_ai.scorer import mean
from inspect_scout._scanner.result import Result
from inspect_scout._scanner.scanner import Scanner, scanner
from inspect_scout._scanner.scorer import as_scorer
from inspect_scout._transcript.types import Transcript


@scanner(messages="all")
def my_scanner() -> Scanner[Transcript]:
    async def scan(_transcript: Transcript) -> Result:
        return Result(value=1)

    return scan


def test_scanner_as_scorer_explicit() -> None:
    task = Task(scorer=as_scorer(my_scanner()))
    log = eval(tasks=task, model="mockllm/model")[0]
    assert log.status == "success"


def test_scanner_as_scorer_implicit() -> None:
    task = Task(scorer=my_scanner())
    log = eval(tasks=task, model="mockllm/model")[0]
    assert log.status == "success"


# Resultset tests


@scanner(messages="all")
def single_result_scanner() -> Scanner[Transcript]:
    """Scanner that returns a resultset with a single result."""

    async def scan(_transcript: Transcript) -> list[Result]:
        return [Result(label="finding", value=True)]

    return scan


@scanner(messages="all")
def multiple_unique_labels_scanner() -> Scanner[Transcript]:
    """Scanner that returns a resultset with multiple unique labels."""

    async def scan(_transcript: Transcript) -> list[Result]:
        return [
            Result(label="deception", value=True),
            Result(label="jailbreak", value=False),
            Result(label="misconfig", value=True),
        ]

    return scan


@scanner(messages="all")
def duplicate_labels_scanner() -> Scanner[Transcript]:
    """Scanner that returns a resultset with duplicate labels (takes first)."""

    async def scan(_transcript: Transcript) -> list[Result]:
        return [
            Result(label="deception", value=True, explanation="First finding"),
            Result(label="jailbreak", value=False),
            Result(label="deception", value=False, explanation="Second finding"),
        ]

    return scan


@scanner(messages="all")
def complex_values_scanner() -> Scanner[Transcript]:
    """Scanner that returns a resultset with complex values (lists, dicts)."""

    async def scan(_transcript: Transcript) -> list[Result]:
        return [
            Result(label="items", value=["a", "b", "c"]),
            Result(label="config", value={"key": "value", "count": 42}),
            Result(label="simple", value=True),
        ]

    return scan


@scanner(messages="all")
def empty_resultset_scanner() -> Scanner[Transcript]:
    """Scanner that returns an empty resultset."""

    async def scan(_transcript: Transcript) -> list[Result]:
        return []

    return scan


@scanner(messages="all")
def unlabeled_result_scanner() -> Scanner[Transcript]:
    """Scanner that returns a resultset with missing label (should error)."""

    async def scan(_transcript: Transcript) -> list[Result]:
        return [
            Result(value=True),  # No label
        ]

    return scan


def test_resultset_single_result() -> None:
    """Test that a resultset with a single result produces a dict-valued score."""
    task = Task(scorer=as_scorer(single_result_scanner(), metrics={"*": [mean()]}))
    log = eval(tasks=task, model="mockllm/model")[0]
    assert log.status == "success"
    # Check that the score value is a dict with the expected label
    assert log.samples is not None
    sample = log.samples[0]
    assert sample.scores is not None
    score = sample.scores["single_result_scanner"]
    assert isinstance(score.value, dict)
    assert score.value == {"finding": True}


def test_resultset_multiple_unique_labels() -> None:
    """Test that a resultset with multiple unique labels produces correct dict."""
    task = Task(scorer=as_scorer(multiple_unique_labels_scanner(), metrics={"*": [mean()]}))
    log = eval(tasks=task, model="mockllm/model")[0]
    assert log.status == "success"
    assert log.samples is not None
    sample = log.samples[0]
    assert sample.scores is not None
    score = sample.scores["multiple_unique_labels_scanner"]
    assert isinstance(score.value, dict)
    assert score.value == {
        "deception": True,
        "jailbreak": False,
        "misconfig": True,
    }


def test_resultset_duplicate_labels_takes_first() -> None:
    """Test that duplicate labels take the first occurrence."""
    task = Task(scorer=as_scorer(duplicate_labels_scanner(), metrics={"*": [mean()]}))
    log = eval(tasks=task, model="mockllm/model")[0]
    assert log.status == "success"
    assert log.samples is not None
    sample = log.samples[0]
    assert sample.scores is not None
    score = sample.scores["duplicate_labels_scanner"]
    assert isinstance(score.value, dict)
    # Should have the first "deception" value (True), not the second (False)
    assert score.value == {
        "deception": True,  # First occurrence
        "jailbreak": False,
    }


def test_resultset_complex_values_serialized() -> None:
    """Test that complex values (lists, dicts) are JSON-serialized."""
    task = Task(scorer=as_scorer(complex_values_scanner(), metrics={"*": [mean()]}))
    log = eval(tasks=task, model="mockllm/model")[0]
    assert log.status == "success"
    assert log.samples is not None
    sample = log.samples[0]
    assert sample.scores is not None
    score = sample.scores["complex_values_scanner"]
    assert isinstance(score.value, dict)
    # Complex values should be serialized as JSON strings
    assert "items" in score.value
    assert isinstance(score.value["items"], str)
    assert "config" in score.value
    assert isinstance(score.value["config"], str)
    # Simple values remain as-is
    assert score.value["simple"] is True


def test_resultset_empty() -> None:
    """Test that an empty resultset produces an empty dict."""
    task = Task(scorer=as_scorer(empty_resultset_scanner(), metrics={"*": [mean()]}))
    log = eval(tasks=task, model="mockllm/model")[0]
    assert log.status == "success"
    assert log.samples is not None
    sample = log.samples[0]
    assert sample.scores is not None
    score = sample.scores["empty_resultset_scanner"]
    assert isinstance(score.value, dict)
    assert score.value == {}


def test_resultset_unlabeled_result_raises_error() -> None:
    """Test that a resultset with unlabeled results raises an error when used as a scorer."""
    task = Task(scorer=as_scorer(unlabeled_result_scanner()))
    log = eval(tasks=task, model="mockllm/model")[0]
    # The eval should complete but with an error status
    assert log.status == "error"
    # The error should be about unlabeled result
    assert log.samples is not None
    sample = log.samples[0]
    assert sample.error is not None
    assert "must have labels" in str(sample.error.message)
