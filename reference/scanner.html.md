# Scanner API


## Scanner

### Scanner

Scan transcript content.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/4cd003160820d009a38a094b5bc4e9c143661c2c/src/inspect_scout/_scanner/scanner.py#L67)

``` python
class Scanner(Protocol[T]):
    def __call__(self, input: T, /) -> Awaitable[Result]
```

`input` T  
Input to scan.

### ScannerInput

Union of all valid scanner input types.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/4cd003160820d009a38a094b5bc4e9c143661c2c/src/inspect_scout/_scanner/types.py#L11)

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

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/4cd003160820d009a38a094b5bc4e9c143661c2c/src/inspect_scout/_scanner/result.py#L22)

``` python
class Result(BaseModel)
```

#### Attributes

`value` JsonValue  
Scan value (can be `None` if the scan didn’t find what is was looking
for).

`explanation` str \| None  
Explanation of result (optional).

`metadata` dict\[str, Any\] \| None  
Additional metadata related to the result (optional)

`references` list\[[Reference](scanner.qmd#reference)\]  
References to relevant messages or events.

### Reference

Reference to scanned content.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/4cd003160820d009a38a094b5bc4e9c143661c2c/src/inspect_scout/_scanner/result.py#L12)

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

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/4cd003160820d009a38a094b5bc4e9c143661c2c/src/inspect_scout/_scanner/result.py#L38)

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

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/4cd003160820d009a38a094b5bc4e9c143661c2c/src/inspect_scout/_scanner/loader.py#L44)

``` python
class Loader(Protocol[TLoaderResult]):
    def __call__(
        self,
        transcript: Transcript,
    ) -> AsyncIterator[TLoaderResult]
```

`transcript` [Transcript](transcript.qmd#transcript)  
Transcript to yield from.

## Utils

### messages_as_str

Concatenate list of chat messages into a string.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/4cd003160820d009a38a094b5bc4e9c143661c2c/src/inspect_scout/_scanner/util.py#L15)

``` python
def messages_as_str(messages: list[ChatMessage]) -> str
```

`messages` list\[ChatMessage\]  
List of chat messages

## Types

### MessageType

Message types.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/4cd003160820d009a38a094b5bc4e9c143661c2c/src/inspect_scout/_transcript/types.py#L10)

``` python
MessageType = Literal["system", "user", "assistant", "tool"]
```

### EventType

Event types.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/4cd003160820d009a38a094b5bc4e9c143661c2c/src/inspect_scout/_transcript/types.py#L13)

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

## Decorators

### scanner

Decorator for registering scanners.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/4cd003160820d009a38a094b5bc4e9c143661c2c/src/inspect_scout/_scanner/scanner.py#L179)

``` python
def scanner(
    factory: ScannerFactory[P, T] | None = None,
    *,
    loader: Loader[T] | None = None,
    messages: list[MessageType] | Literal["all"] | None = None,
    events: list[EventType] | Literal["all"] | None = None,
    name: str | None = None,
) -> (
    ScannerFactory[P, T]
    | Callable[[ScannerFactory[P, T]], ScannerFactory[P, T]]
    | Callable[[ScannerFactory[P, TM]], ScannerFactory[P, ScannerInput]]
    | Callable[[ScannerFactory[P, TE]], ScannerFactory[P, ScannerInput]]
)
```

`factory` ScannerFactory\[P, T\] \| None  
Decorated scanner function.

`loader` [Loader](scanner.qmd#loader)\[T\] \| None  
Custom data loader for scanner.

`messages` list\[[MessageType](scanner.qmd#messagetype)\] \| Literal\['all'\] \| None  
Message types to scan.

`events` list\[[EventType](scanner.qmd#eventtype)\] \| Literal\['all'\] \| None  
Event types to scan.

`name` str \| None  
Scanner name (defaults to function name).

### loader

Decorator for registering loaders.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/4cd003160820d009a38a094b5bc4e9c143661c2c/src/inspect_scout/_scanner/loader.py#L67)

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
