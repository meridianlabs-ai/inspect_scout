# Scanner API


## Scanner

### Scanner

Scan transcript content.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/cd331a8f1d1dcf57d42d14df5c7627b7453bd306/src/inspect_scout/_scanner/scanner.py#L81)

``` python
class Scanner(Protocol[T]):
    def __call__(self, input: T, /) -> Awaitable[Result | list[Result]]
```

`input` T  
Input to scan.

### ScannerInput

Union of all valid scanner input types.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/cd331a8f1d1dcf57d42d14df5c7627b7453bd306/src/inspect_scout/_scanner/types.py#L12)

``` python
ScannerInput = Union[
    Transcript,
    ChatMessage,
    Sequence[ChatMessage],
    Event,
    Sequence[Event],
    Timeline,
    Sequence[Timeline],
]
```

### Result

Scan result.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/cd331a8f1d1dcf57d42d14df5c7627b7453bd306/src/inspect_scout/_scanner/result.py#L31)

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

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/cd331a8f1d1dcf57d42d14df5c7627b7453bd306/src/inspect_scout/_scanner/result.py#L15)

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

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/cd331a8f1d1dcf57d42d14df5c7627b7453bd306/src/inspect_scout/_scanner/result.py#L63)

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

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/cd331a8f1d1dcf57d42d14df5c7627b7453bd306/src/inspect_scout/_scanner/loader.py#L48)

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

Messages are extracted via `transcript_messages()`, which automatically
selects the best strategy (timelines → events → raw messages) and
respects context window limits. Each segment is scanned independently
with globally unique message numbering (`[M1]`, `[M2]`, …) across all
segments.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/cd331a8f1d1dcf57d42d14df5c7627b7453bd306/src/inspect_scout/_llm_scanner/_llm_scanner.py#L76)

``` python
@scanner(messages="all")
def llm_scanner(
    *,
    question: str | Callable[[Transcript], Awaitable[str]] | None = None,
    answer: AnswerSpec,
    value_to_float: ValueToFloat | None = None,
    template: str | None = None,
    template_variables: dict[str, Any]
    | Callable[[Transcript], dict[str, Any]]
    | None = None,
    preprocessor: MessagesPreprocessor[Transcript] | None = None,
    model: str | Model | None = None,
    model_role: str | None = None,
    retry_refusals: bool | int = 3,
    name: str | None = None,
    content: TranscriptContent | None = None,
    context_window: int | None = None,
    compaction: Literal["all", "last"] | int = "all",
    depth: int | None = None,
    reducer: Callable[[list[Result]], Awaitable[Result]] | None = None,
) -> Scanner[Transcript]
```

`question` str \| Callable\[\[[Transcript](transcript.qmd#transcript)\], Awaitable\[str\]\] \| None  
Question for the scanner to answer. Can be a static string (e.g., “Did
the assistant refuse the request?”) or a function that takes a
Transcript and returns an string for dynamic questions based on
transcript content. Can be omitted if you provide a custom template.

`answer` [AnswerSpec](scanner.qmd#answerspec)  
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
system messages. Note: custom `transform` functions that accept a
`Transcript` are not supported when `context_window` or timeline
scanning produces multiple segments, as the transform receives
`list[ChatMessage]` per segment.

`model` str \| Model \| None  
Optional model specification. Can be a model name string or `Model`
instance. If None, uses the default model.

`model_role` str \| None  
Optional model role for role-based model resolution. When set, the model
is resolved via `get_model(model, role=model_role)` at scan time,
allowing deferred role resolution when roles are not yet available at
scanner construction time.

`retry_refusals` bool \| int  
Retry model refusals. Pass an `int` for number of retries (defaults to
3). Pass `False` to not retry refusals. If the limit of refusals is
exceeded then a `RuntimeError` is raised.

`name` str \| None  
Scanner name. Use this to assign a name when passing `llm_scanner()`
directly to `scan()` rather than delegating to it from another scanner.

`content` [TranscriptContent](scanner.qmd#transcriptcontent) \| None  
Override the transcript content filters for this scanner. For example,
`TranscriptContent(timeline=True)` requests timeline data so the scanner
can process span-level segments.

`context_window` int \| None  
Override the model’s context window size for chunking. When set,
transcripts exceeding this limit are split into multiple segments, each
scanned independently.

`compaction` Literal\['all', 'last'\] \| int  
How to handle compaction boundaries when extracting messages from
events. `"all"` (default) scans all compaction segments; `"last"` scans
only the most recent.

`depth` int \| None  
Maximum depth of the span tree to process when timelines are present.
`None` (default) processes all depths. Ignored for events-only or
messages-only transcripts.

`reducer` Callable\[\[list\[[Result](scanner.qmd#result)\]\], Awaitable\[[Result](scanner.qmd#result)\]\] \| None  
Custom reducer for aggregating multi-segment results. Accepts any
`Callable[[list[Result]], Awaitable[Result]]`. If None, uses a default
reducer based on the answer type (e.g., `ResultReducer.any` for boolean,
`ResultReducer.mean` for numeric). Standard reducers are available on
:class:`ResultReducer`. Timeline and resultset answers bypass reduction
and return a resultset.

### grep_scanner

Pattern-based transcript scanner.

Scans transcript messages and events for text patterns using grep-style
matching. By default, patterns are treated as literal strings (like grep
without -E). Set `regex=True` to treat patterns as regular expressions.

What gets searched depends on what’s populated in the transcript: -
Messages are searched if `transcript.messages` is populated - Events are
searched if `transcript.events` is populated - Control population via
`@scanner(messages=..., events=...)`

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/cd331a8f1d1dcf57d42d14df5c7627b7453bd306/src/inspect_scout/_grep_scanner/_grep_scanner.py#L14)

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

## Scanner Tools

> [!NOTE]
>
> The scanner tools functions described below are available only in the
> development version of Inspect Scout. Install the development version
> from GitHub with:
>
> ``` python
> pip install git+https://github.com/meridianlabs-ai/inspect_scout
> ```

### message_numbering

Create a messages_as_str / extract_references pair with shared
numbering.

Returns two functions that share a closure-captured counter and id_map.
Each call to the returned messages_as_str auto-increments message IDs
globally, so multiple calls produce M1..M5, then M6..M10, etc.

The returned extract_references resolves citations from ANY prior
messages_as_str call within this numbering scope.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/cd331a8f1d1dcf57d42d14df5c7627b7453bd306/src/inspect_scout/_scanner/extract.py#L143)

``` python
def message_numbering(
    preprocessor: MessagesPreprocessor[list[ChatMessage]] | None = None,
) -> tuple[MessagesAsStr, ExtractReferences]
```

`preprocessor` [MessagesPreprocessor](scanner.qmd#messagespreprocessor)\[list\[ChatMessage\]\] \| None  
Message preprocessing options applied to every call (e.g.,
exclude_system, exclude_reasoning). Defaults to excluding system
messages when no preprocessor is provided.

### scanner_prompt

Render the default scanner prompt template.

Combines the transcript messages, question, and answer type into a
complete prompt using the standard scanner template. Use this when you
want the default prompt structure but need control over generation (via
`generate_answer()`) or other scanning steps.

For fully custom prompt templates, use `answer_type()` to access the
`.prompt` and `.format` strings directly.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/cd331a8f1d1dcf57d42d14df5c7627b7453bd306/src/inspect_scout/_llm_scanner/generate.py#L163)

``` python
def scanner_prompt(
    messages: str,
    question: str,
    answer: AnswerSpec | Answer,
) -> str
```

`messages` str  
Pre-formatted message string (from `messages_as_str` or
`message_numbering`).

`question` str  
Question for the scanner to answer.

`answer` [AnswerSpec](scanner.qmd#answerspec) \| [Answer](scanner.qmd#answer)  
Answer specification or resolved `Answer` object.

### generate_answer

Generate a model response, optionally parsing it into a Result.

Dispatches to the appropriate generation strategy based on the answer
type: tool-based structured generation for :class:`AnswerStructured`,
standard text generation with refusal retry for all other types.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/cd331a8f1d1dcf57d42d14df5c7627b7453bd306/src/inspect_scout/_llm_scanner/generate.py#L81)

``` python
async def generate_answer(
    prompt: str | list[ChatMessage],
    answer: AnswerSpec,
    *,
    model: str | Model | None = None,
    retry_refusals: int = 3,
    parse: bool = True,
    extract_refs: Callable[[str], list[Reference]] | None = None,
    value_to_float: ValueToFloat | None = None,
) -> Result | ModelOutput
```

`prompt` str \| list\[ChatMessage\]  
The scanning prompt (string or message list).

`answer` [AnswerSpec](scanner.qmd#answerspec)  
Answer specification (`"boolean"`, `"numeric"`, `"string"`, `list[str]`,
or :class:`AnswerStructured`). Determines both the generation strategy
and (when parsing) how to extract the result.

`model` str \| Model \| None  
Model to use for generation. Can be a model name string or `Model`
instance. If `None`, uses the default model.

`retry_refusals` int  
Number of times to retry on model refusals
(`stop_reason == "content_filter"`).

`parse` bool  
When `True` (default), parse the model output into a :class:`Result`.
When `False`, return the raw :class:`ModelOutput`.

`extract_refs` Callable\[\[str\], list\[[Reference](scanner.qmd#reference)\]\] \| None  
Function to extract `[M1]`-style references from the explanation text.
Only used when `parse=True`. Defaults to a no-op that returns no
references.

`value_to_float` ValueToFloat \| None  
Optional function to convert the parsed value to a float. Only used when
`parse=True`.

### parse_answer

Parse a model output into a Result using the answer specification.

Delegates to the answer type’s parsing logic. This is a pure function —
no LLM call is made.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/cd331a8f1d1dcf57d42d14df5c7627b7453bd306/src/inspect_scout/_llm_scanner/generate.py#L30)

``` python
def parse_answer(
    output: ModelOutput,
    answer: AnswerSpec,
    extract_refs: Callable[[str], list[Reference]],
    value_to_float: ValueToFloat | None = None,
) -> Result
```

`output` ModelOutput  
The model’s response to parse.

`answer` [AnswerSpec](scanner.qmd#answerspec)  
Answer specification (`"boolean"`, `"numeric"`, `"string"`, `list[str]`,
or :class:`AnswerStructured`).

`extract_refs` Callable\[\[str\], list\[[Reference](scanner.qmd#reference)\]\]  
Function to extract `[M1]`-style references from the explanation text.

`value_to_float` ValueToFloat \| None  
Optional function to convert the parsed value to a float.

### ResultReducer

Standard reducers for aggregating multi-segment scan results.

Each static method is an async reducer with signature
`(list[Result]) -> Result`. The :meth:`llm` factory returns a reducer
that uses an LLM to synthesize results.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/cd331a8f1d1dcf57d42d14df5c7627b7453bd306/src/inspect_scout/_llm_scanner/_reducer.py#L77)

``` python
class ResultReducer
```

#### Methods

mean  
Arithmetic mean of numeric values.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/cd331a8f1d1dcf57d42d14df5c7627b7453bd306/src/inspect_scout/_llm_scanner/_reducer.py#L85)

``` python
@staticmethod
async def mean(results: list[Result]) -> Result
```

`results` list\[[Result](scanner.qmd#result)\]  

median  
Median of numeric values.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/cd331a8f1d1dcf57d42d14df5c7627b7453bd306/src/inspect_scout/_llm_scanner/_reducer.py#L94)

``` python
@staticmethod
async def median(results: list[Result]) -> Result
```

`results` list\[[Result](scanner.qmd#result)\]  

mode  
Mode (most common) of numeric values.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/cd331a8f1d1dcf57d42d14df5c7627b7453bd306/src/inspect_scout/_llm_scanner/_reducer.py#L103)

``` python
@staticmethod
async def mode(results: list[Result]) -> Result
```

`results` list\[[Result](scanner.qmd#result)\]  

max  
Maximum of numeric values.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/cd331a8f1d1dcf57d42d14df5c7627b7453bd306/src/inspect_scout/_llm_scanner/_reducer.py#L112)

``` python
@staticmethod
async def max(results: list[Result]) -> Result
```

`results` list\[[Result](scanner.qmd#result)\]  

min  
Minimum of numeric values.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/cd331a8f1d1dcf57d42d14df5c7627b7453bd306/src/inspect_scout/_llm_scanner/_reducer.py#L121)

``` python
@staticmethod
async def min(results: list[Result]) -> Result
```

`results` list\[[Result](scanner.qmd#result)\]  

any  
Boolean OR — True if any result is True.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/cd331a8f1d1dcf57d42d14df5c7627b7453bd306/src/inspect_scout/_llm_scanner/_reducer.py#L130)

``` python
@staticmethod
async def any(results: list[Result]) -> Result
```

`results` list\[[Result](scanner.qmd#result)\]  

union  
Union of list values, deduplicated, preserving order.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/cd331a8f1d1dcf57d42d14df5c7627b7453bd306/src/inspect_scout/_llm_scanner/_reducer.py#L137)

``` python
@staticmethod
async def union(results: list[Result]) -> Result
```

`results` list\[[Result](scanner.qmd#result)\]  

majority  
Most common value, with last-result tiebreaker.

Counts occurrences of each `value` across results. If there is a unique
winner it is used; otherwise the last result’s value breaks the tie. The
`answer` is taken from the matching result.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/cd331a8f1d1dcf57d42d14df5c7627b7453bd306/src/inspect_scout/_llm_scanner/_reducer.py#L152)

``` python
@staticmethod
async def majority(results: list[Result]) -> Result
```

`results` list\[[Result](scanner.qmd#result)\]  

last  
Return the last result with merged auxiliary fields.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/cd331a8f1d1dcf57d42d14df5c7627b7453bd306/src/inspect_scout/_llm_scanner/_reducer.py#L187)

``` python
@staticmethod
async def last(results: list[Result]) -> Result
```

`results` list\[[Result](scanner.qmd#result)\]  

llm  
Factory that returns an LLM-based reducer.

The returned reducer formats all segment results into a prompt and asks
the model to synthesize the best answer.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/cd331a8f1d1dcf57d42d14df5c7627b7453bd306/src/inspect_scout/_llm_scanner/_reducer.py#L197)

``` python
@staticmethod
def llm(
    model: str | Model | None = None,
    prompt: str | None = None,
) -> Callable[[list[Result]], Awaitable[Result]]
```

`model` str \| Model \| None  
Model to use for synthesis. Defaults to the default model.

`prompt` str \| None  
Custom synthesis prompt template. If None, uses a default template.

### Answer

Protocol for LLM scanner answer types.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/cd331a8f1d1dcf57d42d14df5c7627b7453bd306/src/inspect_scout/_llm_scanner/answer.py#L65)

``` python
@runtime_checkable
class Answer(Protocol)
```

#### Attributes

`prompt` str  
Return the answer prompt string.

`format` str  
Return the answer format string.

#### Methods

result_for_answer  
Extract and return the result from model output.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/cd331a8f1d1dcf57d42d14df5c7627b7453bd306/src/inspect_scout/_llm_scanner/answer.py#L79)

``` python
def result_for_answer(
    self,
    output: ModelOutput,
    extract_references: Callable[[str], list[Reference]],
    value_to_float: ValueToFloat | None = None,
) -> Result
```

`output` ModelOutput  

`extract_references` Callable\[\[str\], list\[[Reference](scanner.qmd#reference)\]\]  

`value_to_float` ValueToFloat \| None  

### answer_type

Resolve an answer specification into an Answer object.

The returned object exposes `.prompt` and `.format` properties
containing the prompt text and format instructions for the answer type.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/cd331a8f1d1dcf57d42d14df5c7627b7453bd306/src/inspect_scout/_llm_scanner/answer.py#L112)

``` python
def answer_type(
    answer: Literal["boolean", "numeric", "string"]
    | list[str]
    | AnswerMultiLabel
    | AnswerStructured,
) -> Answer
```

`answer` Literal\['boolean', 'numeric', 'string'\] \| list\[str\] \| [AnswerMultiLabel](scanner.qmd#answermultilabel) \| [AnswerStructured](scanner.qmd#answerstructured)  
Answer specification (`"boolean"`, `"numeric"`, `"string"`, `list[str]`,
`AnswerMultiLabel`, or `AnswerStructured`).

### AnswerSpec

Specification of the answer format for an LLM scanner.

Pass `"boolean"`, `"numeric"`, or `"string"` for a simple answer; pass
`list[str]` for a set of labels; pass :class:`AnswerMultiLabel` for
multi-classification; or pass :class:`AnswerStructured` for tool-based
structured output.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/cd331a8f1d1dcf57d42d14df5c7627b7453bd306/src/inspect_scout/_llm_scanner/types.py#L49)

``` python
AnswerSpec: TypeAlias = (
    Literal["boolean", "numeric", "string"]
    | list[str]
    | AnswerMultiLabel
    | AnswerStructured
)
```

### AnswerMultiLabel

Label descriptions for LLM scanner multi-classification.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/cd331a8f1d1dcf57d42d14df5c7627b7453bd306/src/inspect_scout/_llm_scanner/types.py#L6)

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

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/cd331a8f1d1dcf57d42d14df5c7627b7453bd306/src/inspect_scout/_llm_scanner/types.py#L16)

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

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/cd331a8f1d1dcf57d42d14df5c7627b7453bd306/src/inspect_scout/_scanner/extract.py#L75)

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

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/cd331a8f1d1dcf57d42d14df5c7627b7453bd306/src/inspect_scout/_scanner/extract.py#L22)

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

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/cd331a8f1d1dcf57d42d14df5c7627b7453bd306/src/inspect_scout/_scanner/extract.py#L40)

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

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/cd331a8f1d1dcf57d42d14df5c7627b7453bd306/src/inspect_scout/_scanner/extract.py#L331)

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

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/cd331a8f1d1dcf57d42d14df5c7627b7453bd306/src/inspect_scout/_transcript/types.py#L16)

``` python
MessageType = Literal["system", "user", "assistant", "tool"]
```

### EventType

Event types.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/cd331a8f1d1dcf57d42d14df5c7627b7453bd306/src/inspect_scout/_transcript/types.py#L47)

``` python
EventType = Literal[
    "model",
    "tool",
    "compaction",
    "approval",
    "sandbox",
    "info",
    "store",
    "logger",
    "error",
    "span_begin",
    "span_end",
]
```

### TranscriptContent

Content filters for transcript loading.

Specifies which messages, events, and timeline data to include when
loading transcript content for scanning.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/cd331a8f1d1dcf57d42d14df5c7627b7453bd306/src/inspect_scout/_transcript/types.py#L71)

``` python
@dataclass
class TranscriptContent
```

#### Attributes

`messages` MessageFilter  
Filter for which message types to include.

`events` EventFilter  
Filter for which event types to include.

`timeline` TimelineFilter  
Filter for which timeline events to include.

### RefusalError

Error indicating that the model refused a scan request.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/cd331a8f1d1dcf57d42d14df5c7627b7453bd306/src/inspect_scout/_util/refusal.py#L7)

``` python
class RefusalError(RuntimeError)
```

## Registration

### scanner

Decorator for registering scanners.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/cd331a8f1d1dcf57d42d14df5c7627b7453bd306/src/inspect_scout/_scanner/scanner.py#L230)

``` python
def scanner(
    factory: ScannerFactory[P, T] | None = None,
    *,
    loader: Loader[TScan] | None = None,
    messages: list[MessageType] | Literal["all"] | None = None,
    events: list[EventType] | Literal["all"] | None = None,
    timeline: Literal[True] | list[EventType] | Literal["all"] | None = None,
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

`timeline` Literal\[True\] \| list\[[EventType](scanner.qmd#eventtype)\] \| Literal\['all'\] \| None  
Event types to include in timelines.

`name` str \| None  
Scanner name (defaults to function name).

`version` int  
Scanner version (defaults to 0).

`metrics` Sequence\[Metric \| Mapping\[str, Sequence\[Metric\]\]\] \| Mapping\[str, Sequence\[Metric\]\] \| None  
One or more metrics to calculate over the values (only used if scanner
is converted to a scorer via `as_scorer()`).

### loader

Decorator for registering loaders.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/cd331a8f1d1dcf57d42d14df5c7627b7453bd306/src/inspect_scout/_scanner/loader.py#L151)

``` python
def loader(
    *,
    name: str | None = None,
    messages: list[MessageType] | Literal["all"] | None = None,
    events: list[EventType] | Literal["all"] | None = None,
    timeline: Literal[True] | list[EventType] | Literal["all"] | None = None,
    content: TranscriptContent | None = None,
) -> Callable[[LoaderFactory[P, TLoaderResult]], LoaderFactory[P, TLoaderResult]]
```

`name` str \| None  
Loader name (defaults to function name).

`messages` list\[[MessageType](scanner.qmd#messagetype)\] \| Literal\['all'\] \| None  
Message types to load from.

`events` list\[[EventType](scanner.qmd#eventtype)\] \| Literal\['all'\] \| None  
Event types to load from.

`timeline` Literal\[True\] \| list\[[EventType](scanner.qmd#eventtype)\] \| Literal\['all'\] \| None  
Event types to include in timelines.

`content` [TranscriptContent](scanner.qmd#transcriptcontent) \| None  
Transcript content filter.

### as_scorer

Convert a `Scanner` to an Inspect `Scorer`.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/cd331a8f1d1dcf57d42d14df5c7627b7453bd306/src/inspect_scout/_scanner/scorer.py#L27)

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
