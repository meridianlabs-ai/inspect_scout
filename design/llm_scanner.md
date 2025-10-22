


```python

@dataclass
class Preprocessor:
    exclude_system: bool = True
    exclude_reasoning: bool = False
    exclude_tool_calls: bool = False


@dataclass
class Answer:
    type: Literal["number", "bool", "str", "labels"]
    labels: list[str]
    multi_classification: bool = False


DEFAULT_SCANNER_TEMPLATE = """
{prompt}

Here is the conversation:

{messages}

"""

@scanner
def llm_scanner(
    prompt: str,
    scanner_template: str | None = None,
    model: str | Model | None = None
    preprocessor: Preprocessor,
    answer: Answer | None = None,
) -> Scanner[Transcript]:

    # TODO: when creating the messages, we need to include local 'message ids' for each one
    # (and keep a map of them back to the actual message ids -- use that to populate references)

    async def scan(transcript: Transcript) -> Result:
        
        model = get_model(model)


        

        return Result(value=None)

    return scan


```