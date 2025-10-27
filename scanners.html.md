# Scanners


## Overview

Scanners are the main unit of processing in Inspect Scout and can target
a wide variety of content types. In this article we’ll cover the basic
scanning concepts, and then drill into creating scanners that target
various types (`Transcript`, `Event`, or `ChatMessage`) as well as
creating custom loaders which enable scanning of lists of events or
messages.

## Scanner Basics

A `Scanner` is a function that takes a `ScannerInput` (typically a
`Transcript`, but possibly an `Event`, `ChatMessage`, or list of events
or messages) and returns a `Result`. The result includes a `value` which
can be of any type—this might be `True` to indicate that something was
found but might equally be a number to indicate a count. More elaborate
scanner values (`dict` or `list`) are also possible.

Here is a simple scanner that uses a model to look for agent
“confusion”—whether or not it finds confusion, it still returns the
model completion as an `explanation`:

``` python
@scanner(messages="all")
def confusion() -> Scanner[Transcript]:
    
    async def scan(transcript: Transcript) -> Result:

        # call model
        output = await get_model().generate(
            "Here is a transcript of an LLM agent " +
            "solving a puzzle:\n\n" +
            "===================================" +
            messages_as_str(transcript.messages) +
            "===================================\n\n" +
            "In the transcript above do you see the agent " +
            "becoming confused? Repond beginning with 'Yes' " +
            "or 'No', followed by an explanation."
        )

        # extract the first word
        match = re.match(r"^\w+", output.completion.strip())

        # return result
        if match:
            answer = match.group(0)
            return Result(
                value=answer.lower() == "yes",
                answer=answer,
                explanation=output.completion,
            )
        else:
            return Result(value=False, explanation=output.completion)

    return scan
```

If a scanner doesn’t find anything, it still returns a `Result` with
`value=None` so that the explanation is preserved for later review.

### Input Types

`Transcript` is the most common `ScannerInput` however several other
types are possible:

- `Event` — Single event from the transcript (e.g. `ModelEvent`,
  `ToolEvent`, etc.). More than one `Event` in a `Transcript` can be
  scanned.

- `ChatMessage` — Single chat message from the transcript message
  history. More than one `ChatMessage` in a `Transcript` can be scanned.

- `list[Event]` or `list[ChatMessage]` — Arbitrary sets of events or
  messages extracted from the `Transcript` (see [Loaders](#loaders)
  below for details).

See the sections on [Transcripts](#transcripts), [Events](#events),
[Messages](#messages), and [Loaders](#loaders) below for additional
details on handling various input types.

### Input Filtering

One important principle of the Inspect Scout transcript pipeline is that
only the precise data to be scanned should be read, and nothing more.
This can dramatically improve performance as messages and events that
won’t be seen by scanners are never deserialized. Scanner input filters
are specified as arguments to the `@scanner` decorator (you may have
noticed the `messages="all"` attached to the scanner decorator in the
example above).

For example, here we are looking for instances of assistants
swearing—for this task we only need to look at assistant messages so we
specify `messages=["assistant"]`

``` python
@scanner(messages=["assistant"])
def assistant_swearing() -> Scanner[Transcript]:

    async def scan(transcript: Transcript) -> Result:
        swear_words = [
            word 
            for m in transcript.messages 
            for word in extract_swear_words(m.text)
        ]
        return Result(
            value=len(swear_words),
            explanation=",".join(swear_words)
        )

    return scan
```

With this filter, only assistant messages and no events whatsoever will
be loaded from transcripts during scanning.

Note that by default, no filters are active, so if you don’t specify
values for `messages` and/or `events` your scanner will not be called!

## Transcripts

Transcripts are the most common input to scanners, and are read from one
or more Inspect logs. A `Transcript` represents a single epoch from an
Inspect sample—so each Inspect log file will have `samples * epochs`
transcripts.

### Transcript Fields

Each `Transcript` has the following fields:

| Field | Type | Description |
|----|----|----|
| `id` | str | Globally unique identifier for a transcript (maps to `EvalSample.uuid` in the Inspect log). |
| `source_id` | str | Globally unique identifier for a transcript source (maps to `eval_id` in the Inspect log) |
| `source_uri` | str | URI for source data (e.g. full path to the Inspect log file). |
| `metadata` | dict\[str, JsonValue\] | Eval configuration metadata (e.g. task, model, scores, etc.). See `LogMetadata` for details. |
| `messages` | list\[ChatMessage\] | Message history from `EvalSample` |
| `events` | list\[Event\] | Event history from `EvalSample` |

### Content Filtering

Note that the `messages` and `events` fields will not be populated
unless you specify a `messages` or `events` filter on your scanner. For
example, this scanner will see all messages and events:

``` python
@scanner(messages="all", events="all")
def my_scanner() -> Scanner[Transcript]: ...
```

This scanner will see only model and tool events:

``` python
@scanner(events=["model", "tool"])
def my_scanner() -> Scanner[Transcript]: ...
```

This scanner will see only assistant messages:

``` python
@scanner(messages=["assistant"])
def my_scanner() -> Scanner[Transcript]: ...
```

### Presenting Messages

When processing transcripts, you will often want to present an entire
message history to model for analysis. Above, we used the
`messages_as_str()` function to do this:

``` python
# call model
result = await get_model().generate(
    "Here is a transcript of an LLM agent " +
    "solving a puzzle:\n\n" +
    "===================================" +
    messages_as_str(transcript.messages) +
    "===================================\n\n" +
    "In the transcript above do you see the agent " +
    "becoming confused? Repond beginning with 'Yes' " +
    "or 'No', followed by an explanation."
)
```

## Events

To write a scanner that targets events, write a function that takes the
event type(s) you want to process. For example, this scanner will see
only model events:

``` python
@scanner
def my_scanner() -> Scanner[ModelEvent]:
    def scan(event: ModelEvent) -> Result: 
        ...

    return scan
```

Note that the `events="model"` filter was not required since we had
already declared our scanner to take only model events. If we wanted to
take both model and tool events we’d do this:

``` python
@scanner
def my_scanner() -> Scanner[ModelEvent | ToolEvent]:
    def scan(event: ModelEvent | ToolEvent) -> Result: 
        ...

    return scan
```

## Messages

To write a scanner that targets messages, write a function that takes
the message type(s) you want to process. For example, this scanner will
only see tool messages:

``` python
@scanner
def my_scanner() -> Scanner[ChatMessageTool]:
    def scan(message: ChatMessageTool) -> Result: 
        ...

    return scan
```

This scanner will see only user and assistant messages:

``` python
@scanner
def my_scanner() -> Scanner[ChatMessageUser | ChatMessageAssistant]:
    def scan(message: ChatMessageUser | ChatMessageAssistant) -> Result: 
        ...

    return scan
```

## Loaders

When you want to process multiple discrete items from a `Transcript`
this might not always fall neatly into single messages or events. For
example, you might want to process pairs of user/assistant messages. To
do this, create a custom `Loader` that yields the content as required.

For example, here is a `Loader` that yields user/assistant message
pairs:

``` python
@loader(messages=["user", "assistant"])
def conversation_turns():
    async def load(
        transcript: Transcript
    ) -> AsyncGenerator[list[ChatMessage], None]:
        
        for user,assistant in message_pairs(transcript.messages):
            yield [user, assistant]

    return load
```

Note that just like with scanners, the loader still needs to provide a
`messages=["user", "assistant"]` in order to see those messages.

We can now use this loader in a scanner that looks for refusals:

``` python
@scanner(loader=conversation_turns())
def assistant_refusals() -> Scanner[list[ChatMessage]]:

    async def scan(messages: list[ChatMessage]) -> Result:
        user, assistant = messages
        return Result(
            value=is_refusal(assistant.text), 
            explanation=messages_as_str(messages)
        )

    return scan
```
