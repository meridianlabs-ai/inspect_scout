from inspect_ai import Task, eval
from inspect_scout._scanner.result import Result
from inspect_scout._scanner.scanner import Scanner, scanner
from inspect_scout._scanner.scorer import as_scorer
from inspect_scout._transcript.types import Transcript


@scanner(messages="all")
def my_scanner() -> Scanner[Transcript]:
    async def scan(transcript: Transcript) -> Result:
        return Result(value=1)

    return scan


def test_scanner_as_scorer() -> None:
    task = Task(scorer=as_scorer(my_scanner()))
    log = eval(tasks=task, model="mockllm/model")[0]
    assert log.status == "success"
