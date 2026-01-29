# Scanner API


## Scanner

### Scanner

Scan transcript content.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/0f556baa3f7cd9db0e85fbe7976eaab7bf6e9c5c/src/inspect_scout/_scanner/scanner.py#L79)

``` python
class Scanner(Protocol[T]):
    def __call__(self, input: T, /) -> Awaitable[Result | list[Result]]
```

`input` T  
Input to scan.

### ScannerInput

Union of all valid scanner input types.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/0f556baa3f7cd9db0e85fbe7976eaab7bf6e9c5c/src/inspect_scout/_scanner/types.py#L11)

``` python
ScannerInput = Union[
    Transcript,
    ChatMessage,
    Sequence[ChatMessage],
    Event,
    Sequence[Event],
]
```

### Result

Scan result.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/0f556baa3f7cd9db0e85fbe7976eaab7bf6e9c5c/src/inspect_scout/_scanner/result.py#L31)

``` python
class Result(BaseModel)
```

#### Attributes

`uuid` str \| None  
Unique identifer for scan result.

`value` JsonValue  
Scan value.

`answer` str \| None  
Answer extracted from model output (optional)

`explanation` str \| None  
Explanation of result (optional).

`metadata` dict\[str, Any\] \| None  
Additional metadata related to the result (optional)

`references` list\[[Reference](scanner.qmd#reference)\]  
References to relevant messages or events.

`label` str \| None  
Label for result to indicate its origin.

`type` str \| None  
Type to designate contents of ‘value’ (used in `value_type` field in
result data frames).

### Reference

Reference to scanned content.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/0f556baa3f7cd9db0e85fbe7976eaab7bf6e9c5c/src/inspect_scout/_scanner/result.py#L15)

``` python
class Reference(BaseModel)
```

#### Attributes

`type` Literal\['message', 'event'\]  
Reference type.

`cite` str \| None  
Cite text used when the entity was referenced (optional).

For example, a model may have pointed to a message using something like
\[M22\], which is the cite.

`id` str  
Reference id (message or event id)

### Error

Scan error (runtime error which occurred during scan).

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/0f556baa3f7cd9db0e85fbe7976eaab7bf6e9c5c/src/inspect_scout/_scanner/result.py#L63)

``` python
class Error(BaseModel)
```

#### Attributes

`transcript_id` str  
Target transcript id.

`scanner` str  
Scanner name.

`error` str  
Error message.

`traceback` str  
Error traceback.

`refusal` bool  
Was this error a refusal.

### Loader

Load transcript data.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/0f556baa3f7cd9db0e85fbe7976eaab7bf6e9c5c/src/inspect_scout/_scanner/loader.py#L47)

``` python
class Loader(Protocol[TLoaderResult]):
    def __call__(
        self,
        transcript: Transcript,
    ) -> AsyncIterator[TLoaderResult]
```

`transcript` [Transcript](transcript.qmd#transcript)  
Transcript to yield from.

## Scanners

### llm_scanner

Create a scanner that uses an LLM to scan transcripts.

This scanner presents a conversation transcript to an LLM along with a
custom prompt and answer specification, enabling automated analysis of
conversations for specific patterns, behaviors, or outcomes.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/0f556baa3f7cd9db0e85fbe7976eaab7bf6e9c5c/src/inspect_scout/_llm_scanner/_llm_scanner.py#L63)

``` python
@scanner(messages="all")
def llm_scanner(
    *,
    question: str | Callable[[Transcript], Awaitable[str]] | None = None,
    answer: Literal["boolean", "numeric", "string"]
    | list[str]
    | AnswerMultiLabel
    | AnswerStructured,
    value_to_float: ValueToFloat | None = None,
    template: str | None = None,
    template_variables: dict[str, Any]
    | Callable[[Transcript], dict[str, Any]]
    | None = None,
    preprocessor: MessagesPreprocessor[Transcript] | None = None,
    model: str | Model | None = None,
    retry_refusals: bool | int = 3,
    name: str | None = None,
) -> Scanner[Transcript]
```

`question` str \| Callable\[\[[Transcript](transcript.qmd#transcript)\], Awaitable\[str\]\] \| None  
Question for the scanner to answer. Can be a static string (e.g., “Did
the assistant refuse the request?”) or a function that takes a
Transcript and returns an string for dynamic questions based on
transcript content. Can be omitted if you provide a custom template.

`answer` Literal\['boolean', 'numeric', 'string'\] \| list\[str\] \| [AnswerMultiLabel](scanner.qmd#answermultilabel) \| [AnswerStructured](scanner.qmd#answerstructured)  
Specification of the answer format. Pass “boolean”, “numeric”, or
“string” for a simple answer; pass `list[str]` for a set of labels; or
pass `MultiLabels` for multi-classification.

`value_to_float` ValueToFloat \| None  
Optional function to convert the answer value to a float.

`template` str \| None  
Overall template for scanner prompt. The scanner template should include
the following variables: - {{ question }} (question for the model to
answer) - {{ messages }} (transcript message history as string) - {{
answer_prompt }} (prompt for a specific type of answer). - {{
answer_format }} (instructions on how to format the answer) In addition,
scanner templates can bind to any data within `Transcript.metadata`
(e.g. {{ metadata.score }})

`template_variables` dict\[str, Any\] \| Callable\[\[[Transcript](transcript.qmd#transcript)\], dict\[str, Any\]\] \| None  
Additional variables to make available in the template. Optionally takes
a function which receives the current `Transcript` which can return
variables.

`preprocessor` [MessagesPreprocessor](scanner.qmd#messagespreprocessor)\[[Transcript](transcript.qmd#transcript)\] \| None  
Transform conversation messages before analysis. Controls exclusion of
system messages, reasoning tokens, and tool calls. Defaults to removing
system messages.

`model` str \| Model \| None  
Optional model specification. Can be a model name string or `Mode`l
instance. If None, uses the default model

`retry_refusals` bool \| int  
Retry model refusals. Pass an `int` for number of retries (defaults to
3). Pass `False` to not retry refusals. If the limit of refusals is
exceeded then a `RuntimeError` is raised.

`name` str \| None  
Scanner name. Use this to assign a name when passing `llm_scanner()`
directly to `scan()` rather than delegating to it from another scanner.

### grep_scanner

Pattern-based transcript scanner.

Scans transcript messages and events for text patterns using grep-style
matching. By default, patterns are treated as literal strings (like grep
without -E). Set `regex=True` to treat patterns as regular expressions.

What gets searched depends on what’s populated in the transcript: -
Messages are searched if `transcript.messages` is populated - Events are
searched if `transcript.events` is populated - Control population via
`@scanner(messages=..., events=...)`

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/0f556baa3f7cd9db0e85fbe7976eaab7bf6e9c5c/src/inspect_scout/_grep_scanner/_grep_scanner.py#L14)

``` python
@scanner(messages="all")
def grep_scanner(
    pattern: str | list[str] | dict[str, str | list[str]],
    *,
    regex: bool = False,
    ignore_case: bool = True,
    word_boundary: bool = False,
    name: str | None = None,
) -> Scanner[Transcript]
```

`pattern` str \| list\[str\] \| dict\[str, str \| list\[str\]\]  
Pattern(s) to search for. Can be: - str: Single pattern - list\[str\]:
Multiple patterns (OR logic, single aggregated result) - dict\[str, str
\| list\[str\]\]: Labeled patterns (returns multiple results, one per
label)

`regex` bool  
If True, treat patterns as regular expressions. Default False (literal
string matching).

`ignore_case` bool  
Case-insensitive matching. Default True (like grep -i).

`word_boundary` bool  
Match whole words only (adds nchors). Default False.

`name` str \| None  
Scanner name. Use this to assign a name when passing `llm_scanner()`
directly to `scan()` rather than delegating to it from another scanner.

#### Examples

Simple pattern (messages only): grep_scanner(“error”)

Multiple patterns (OR logic): grep_scanner(\[“error”, “failed”,
“exception”\])

Labeled patterns (separate results): grep_scanner({ “errors”: \[“error”,
“failed”\], “warnings”: \[“warning”, “caution”\], })

With regex: grep_scanner(r”https?://+“, regex=True)

Search both messages and events: @scanner(messages=“all”,
events=\[“tool”, “error”\]) def find_errors() -\> Scanner\[Transcript\]:
return grep_scanner(“error”)

### AnswerMultiLabel

Label descriptions for LLM scanner multi-classification.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/0f556baa3f7cd9db0e85fbe7976eaab7bf6e9c5c/src/inspect_scout/_llm_scanner/types.py#L6)

``` python
class AnswerMultiLabel(NamedTuple)
```

#### Attributes

`labels` list\[str\]  
List of label descriptions.

Label values (e.g. A, B, C) will be provided automatically.

### AnswerStructured

Answer with structured output.

Structured answers are objects that conform to a JSON Schema.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/0f556baa3f7cd9db0e85fbe7976eaab7bf6e9c5c/src/inspect_scout/_llm_scanner/types.py#L16)

``` python
class AnswerStructured(NamedTuple)
```

#### Attributes

`type` type\[BaseModel\] \| type\[list\]  
Pydantic BaseModel that defines the type of the answer.

Can be a single Pydantic model result or a list of results.

See the docs on [Structured
Answers](https://meridianlabs-ai.github.io/inspect_scout/llm_scanner.html#structured-answers)
for more details on defining types.

See the docs on [Multiple
Results](https://meridianlabs-ai.github.io/inspect_scout/llm_scanner.html#multiple-results)
for details on prompting scanners to yield multiple results from a scan.

`answer_tool` str  
Customize the name of the answer tool provided to the model.

`answer_prompt` str  
Template for prompt that precedes the question posed to the scanner (use
the {{ answer_tool }} variable to refer to the name of the answer tool).

`answer_format` str  
Template for instructions on answer format to place at the end of the
scanner prompt (use the {{ answer_tool }} variable to refer to the name
of the answer tool).

`max_attempts` int  
Maximum number of times to re-prompt the model to generate the correct
schema.

## Utils

### messages_as_str

Concatenate list of chat messages into a string.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/0f556baa3f7cd9db0e85fbe7976eaab7bf6e9c5c/src/inspect_scout/_scanner/extract.py#L75)

``` python
async def messages_as_str(
    input: T,
    *,
    preprocessor: MessagesPreprocessor[T] | None = None,
    include_ids: Literal[True] | None = None,
    as_json: bool = False,
) -> str | tuple[str, Callable[[str], list[Reference]]]
```

`input` T  
The Transcript with the messages or a list of messages.

`preprocessor` [MessagesPreprocessor](scanner.qmd#messagespreprocessor)\[T\] \| None  
Content filter for messages.

`include_ids` Literal\[True\] \| None  
If True, prepend ordinal references (e.g., \[M1\], \[M2\]) to each
message and return a function to extract references from text. If None
(default), return plain formatted string.

`as_json` bool  
If True, output as JSON string instead of plain text.

### MessageFormatOptions

Message formatting options for controlling message content display.

These options control which parts of messages are included when
formatting messages to strings.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/0f556baa3f7cd9db0e85fbe7976eaab7bf6e9c5c/src/inspect_scout/_scanner/extract.py#L22)

``` python
@dataclass(frozen=True)
class MessageFormatOptions
```

#### Attributes

`exclude_system` bool  
Exclude system messages (defaults to `True`)

`exclude_reasoning` bool  
Exclude reasoning content (defaults to `False`).

`exclude_tool_usage` bool  
Exclude tool usage (defaults to `False`)

### MessagesPreprocessor

ChatMessage preprocessing transformations.

Provide a `transform` function for fully custom transformations. Use the
higher-level options (e.g. `exclude_system`) to perform various common
content removal transformations.

The default `MessagesPreprocessor` will exclude system messages and do
no other transformations.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/0f556baa3f7cd9db0e85fbe7976eaab7bf6e9c5c/src/inspect_scout/_scanner/extract.py#L40)

``` python
@dataclass(frozen=True)
class MessagesPreprocessor(MessageFormatOptions, Generic[T])
```

#### Attributes

`exclude_system` bool  
Exclude system messages (defaults to `True`)

`exclude_reasoning` bool  
Exclude reasoning content (defaults to `False`).

`exclude_tool_usage` bool  
Exclude tool usage (defaults to `False`)

`transform` Callable\[\[T\], Awaitable\[list\[ChatMessage\]\]\] \| None  
Transform the list of messages.

### tool_callers

Build a mapping from tool_call_id to the assistant message that made the
call.

This is useful for scanners that need to reference the assistant message
that initiated a tool call, rather than the tool message itself.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/0f556baa3f7cd9db0e85fbe7976eaab7bf6e9c5c/src/inspect_scout/_scanner/extract.py#L281)

``` python
def tool_callers(
    transcript: Transcript,
) -> dict[str, tuple[ChatMessageAssistant, int]]
```

`transcript` [Transcript](transcript.qmd#transcript)  
The transcript containing all messages.

## Types

### MessageType

Message types.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/0f556baa3f7cd9db0e85fbe7976eaab7bf6e9c5c/src/inspect_scout/_transcript/types.py#L12)

``` python
MessageType = Literal["system", "user", "assistant", "tool"]
```

### EventType

Event types.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/0f556baa3f7cd9db0e85fbe7976eaab7bf6e9c5c/src/inspect_scout/_transcript/types.py#L26)

``` python
EventType = Literal[
    "model",
    "tool",
    "approval",
    "sandbox",
    "info",
    "logger",
    "error",
    "span_begin",
    "span_end",
]
```

### RefusalError

Error indicating that the model refused a scan request.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/0f556baa3f7cd9db0e85fbe7976eaab7bf6e9c5c/src/inspect_scout/_util/refusal.py#L7)

``` python
class RefusalError(RuntimeError)
```

## Registration

### scanner

Decorator for registering scanners.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/0f556baa3f7cd9db0e85fbe7976eaab7bf6e9c5c/src/inspect_scout/_scanner/scanner.py#L227)

``` python
def scanner(
    factory: ScannerFactory[P, T] | None = None,
    *,
    loader: Loader[TScan] | None = None,
    messages: list[MessageType] | Literal["all"] | None = None,
    events: list[EventType] | Literal["all"] | None = None,
    name: str | None = None,
    version: int = 0,
    metrics: Sequence[Metric | Mapping[str, Sequence[Metric]]]
    | Mapping[str, Sequence[Metric]]
    | None = None,
) -> (
    ScannerFactory[P, T]
    | Callable[[ScannerFactory[P, T]], ScannerFactory[P, T]]
    | Callable[[ScannerFactory[P, TScan]], ScannerFactory[P, TScan]]
    | Callable[[ScannerFactory[P, TM]], ScannerFactory[P, ScannerInput]]
    | Callable[[ScannerFactory[P, TE]], ScannerFactory[P, ScannerInput]]
)
```

`factory` ScannerFactory\[P, T\] \| None  
Decorated scanner function.

`loader` [Loader](scanner.qmd#loader)\[TScan\] \| None  
Custom data loader for scanner.

`messages` list\[[MessageType](scanner.qmd#messagetype)\] \| Literal\['all'\] \| None  
Message types to scan.

`events` list\[[EventType](scanner.qmd#eventtype)\] \| Literal\['all'\] \| None  
Event types to scan.

`name` str \| None  
Scanner name (defaults to function name).

`version` int  
Scanner version (defaults to 0).

`metrics` Sequence\[Metric \| Mapping\[str, Sequence\[Metric\]\]\] \| Mapping\[str, Sequence\[Metric\]\] \| None  
One or more metrics to calculate over the values (only used if scanner
is converted to a scorer via `as_scorer()`).

### loader

Decorator for registering loaders.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/0f556baa3f7cd9db0e85fbe7976eaab7bf6e9c5c/src/inspect_scout/_scanner/loader.py#L150)

``` python
def loader(
    *,
    name: str | None = None,
    messages: list[MessageType] | Literal["all"] | None = None,
    events: list[EventType] | Literal["all"] | None = None,
    content: TranscriptContent | None = None,
) -> Callable[[LoaderFactory[P, TLoaderResult]], LoaderFactory[P, TLoaderResult]]
```

`name` str \| None  
Loader name (defaults to function name).

`messages` list\[[MessageType](scanner.qmd#messagetype)\] \| Literal\['all'\] \| None  
Message types to load from.

`events` list\[[EventType](scanner.qmd#eventtype)\] \| Literal\['all'\] \| None  
Event types to load from.

`content` TranscriptContent \| None  
Transcript content filter.

### as_scorer

Convert a `Scanner` to an Inspect `Scorer`.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/0f556baa3f7cd9db0e85fbe7976eaab7bf6e9c5c/src/inspect_scout/_scanner/scorer.py#L25)

``` python
def as_scorer(
    scanner: Scanner[Transcript],
    metrics: Sequence[Metric | Mapping[str, Sequence[Metric]]]
    | Mapping[str, Sequence[Metric]]
    | None = None,
) -> Scorer
```

`scanner` [Scanner](scanner.qmd#scanner)\[[Transcript](transcript.qmd#transcript)\]  
Scanner to convert (must take a `Transcript`).

`metrics` Sequence\[Metric \| Mapping\[str, Sequence\[Metric\]\]\] \| Mapping\[str, Sequence\[Metric\]\] \| None  
Metrics for scorer. Defaults to `metrics` specified on the `@scanner`
decorator (or `[mean(), stderr()]` if none were specified).
