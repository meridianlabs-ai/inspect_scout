"""A scanner that always fails — used by CLI exit-code tests."""

from inspect_scout import Result, Scanner, Transcript, scanner


@scanner(messages="all")
def always_fails() -> Scanner[Transcript]:
    async def scan(transcript: Transcript) -> Result:
        raise RuntimeError("intentional scanner failure")

    return scan
