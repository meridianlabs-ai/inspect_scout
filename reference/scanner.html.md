# Scanner API


## Scanner

### Scanner

Scan transcript content.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/0d77f40822e097b404b027f7f472a44c536a2923/src/inspect_scout/_scanner/scanner.py#L76)

``` python
class Scanner(Protocol[T]):
    def __call__(self, input: T, /) -> Awaitable[Result]
```

`input` T  
Input to scan.

### ScannerInput

Union of all valid scanner input types.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/0d77f40822e097b404b027f7f472a44c536a2923/src/inspect_scout/_scanner/types.py#L11)

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

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/0d77f40822e097b404b027f7f472a44c536a2923/src/inspect_scout/_scanner/result.py#L22)

``` python
class Result(BaseModel)
```

#### Attributes

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

### Reference

Reference to scanned content.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/0d77f40822e097b404b027f7f472a44c536a2923/src/inspect_scout/_scanner/result.py#L12)

``` python
class Reference(BaseModel)
```

#### Attributes

`type` Literal\['message', 'event'\]  
Reference type.

`id` str  
Reference id (message or event id)

### Error

Scan error (runtime error which occurred during scan).

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/0d77f40822e097b404b027f7f472a44c536a2923/src/inspect_scout/_scanner/result.py#L41)

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

### Loader

Load transcript data.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/0d77f40822e097b404b027f7f472a44c536a2923/src/inspect_scout/_scanner/loader.py#L47)

``` python
class Loader(Protocol[TLoaderResult]):
    def __call__(
        self,
        transcript: Transcript,
    ) -> AsyncIterator[TLoaderResult]
```

`transcript` [Transcript](transcript.qmd#transcript)  
Transcript to yield from.

## LLM Scanner

### llm_scanner

Create a scanner that uses an LLM to scan transcripts.

This scanner presents a conversation transcript to an LLM along with a
custom prompt and answer specification, enabling automated analysis of
conversations for specific patterns, behaviors, or outcomes.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/0d77f40822e097b404b027f7f472a44c536a2923/src/inspect_scout/_llm_scanner/_llm_scanner.py#L23)

``` python
@scanner(messages="all")
def llm_scanner(
    *,
    question: str,
    answer: Literal["boolean", "numeric", "string"] | list[str] | LLMScannerLabels,
    template: str | None = None,
    messages: ContentFilter | None = None,
    model: str | Model | None = None,
    name: str | None = None,
) -> Scanner[Transcript]
```

`question` str  
Question for the scanner to answer. (e.g., “Did the assistant refuse the
request?”)

`answer` Literal\['boolean', 'numeric', 'string'\] \| list\[str\] \| [LLMScannerLabels](scanner.qmd#llmscannerlabels)  
Specification of the answer format. Pass “boolean”, “numeric”, or
“string” for a simple answer; pass `list[str]` for a set of labels; or
pass `LLMScannerLabels` for multi-classification.

`template` str \| None  
Overall template for scanner prompt. The scanner template should include
the following variables: - {{ question }} (question for the model to
answer) - {{ messages }} (transcript message history as string) - {{
answer_prompt }} (prompt the model for a specific type of answer and
explanation). - {{ answer_format }} (instructions on formatting for
value extraction)

`messages` [ContentFilter](scanner.qmd#contentfilter) \| None  
Filter conversation messages before analysis. Controls exclusion of
system messages, reasoning tokens, and tool calls. Defaults to filtering
system messages.

`model` str \| Model \| None  
Optional model specification. Can be a model name string or Model
instance. If None, uses the default model

`name` str \| None  
Scanner name (use this to assign a name when passing `llm_scanner()`
directly to `scan()` rather than delegating to it from another scanner).

### LLMScannerLabels

Label descriptions for LLM scanner.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/0d77f40822e097b404b027f7f472a44c536a2923/src/inspect_scout/_llm_scanner/types.py#L4)

``` python
class LLMScannerLabels(NamedTuple)
```

#### Attributes

`labels` list\[str\]  
List of label descriptions.

Label values (e.g. A, B, C) will be provided automatically.

`multiple` bool  
Allow answers with multiple labels.

## Utils

### messages_as_str

Concatenate list of chat messages into a string.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/0d77f40822e097b404b027f7f472a44c536a2923/src/inspect_scout/_scanner/extract.py#L27)

``` python
async def messages_as_str(
    messages: list[ChatMessage], filter: ContentFilter | None = None
) -> str
```

`messages` list\[ChatMessage\]  
List of chat messages

`filter` [ContentFilter](scanner.qmd#contentfilter) \| None  
Content filter for messages.

### ContentFilter

Message content options for LLM scanner.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/0d77f40822e097b404b027f7f472a44c536a2923/src/inspect_scout/_scanner/extract.py#L11)

``` python
class ContentFilter(NamedTuple)
```

#### Attributes

`messages` Callable\[\[list\[ChatMessage\]\], Awaitable\[list\[ChatMessage\]\]\] \| None  
Transform the list of messages.

`exclude_system` bool  
Exclude system messages (defaults to `True`)

`exclude_reasoning` bool  
Exclude reasoning content (defaults to `False`).

`exclude_tool_usage` bool  
Exclude tool usage (defaults to `False`)

## Types

### MessageType

Message types.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/0d77f40822e097b404b027f7f472a44c536a2923/src/inspect_scout/_transcript/types.py#L10)

``` python
MessageType = Literal["system", "user", "assistant", "tool"]
```

### EventType

Event types.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/0d77f40822e097b404b027f7f472a44c536a2923/src/inspect_scout/_transcript/types.py#L13)

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

## Registration

### scanner

Decorator for registering scanners.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/0d77f40822e097b404b027f7f472a44c536a2923/src/inspect_scout/_scanner/scanner.py#L215)

``` python
def scanner(
    factory: ScannerFactory[P, T] | None = None,
    *,
    loader: Loader[TScan] | None = None,
    messages: list[MessageType] | Literal["all"] | None = None,
    events: list[EventType] | Literal["all"] | None = None,
    name: str | None = None,
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

`metrics` Sequence\[Metric \| Mapping\[str, Sequence\[Metric\]\]\] \| Mapping\[str, Sequence\[Metric\]\] \| None  
One or more metrics to calculate over the values (only used if scanner
is converted to a scorer via `as_scorer()`).

### loader

Decorator for registering loaders.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/0d77f40822e097b404b027f7f472a44c536a2923/src/inspect_scout/_scanner/loader.py#L150)

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

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/0d77f40822e097b404b027f7f472a44c536a2923/src/inspect_scout/_scanner/scorer.py#L23)

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
decorator (or `[accuracy(), stderr()]` if none were specified).
