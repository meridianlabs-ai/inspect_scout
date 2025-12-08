# Database Schema


## Overview

In a transcript database, the only strictly required field is
`transcript_id` (although you’ll almost always want to also include a
`messages` field as that’s the main thing targeted by most scanners).

You can also include `source_*` fields as a reference to where the
transcript originated as well as arbitrary other fields (trancript
metadata) which are then queryable using the `Transcripts` API.

| Field | Description |
|----|----|
| `transcript_id` | Required. A globally unique identifier for a transcript. |
| `source_type` | Optional. Type of transcript source (e.g. “weave”, “logfire”, “eval_log”, etc.). Useful for providing a hint to readers about what might be available in the `metadata` field. |
| `source_id` | Optional. Globally unique identifier for a transcript source (e.g. a project id). |
| `source_uri` | Optional. URI for source data (e.g. link to a web page or REST resource for discovering more about the transcript). |
| `messages` | Optional. List of [ChatMessage](https://inspect.aisi.org.uk/reference/inspect_ai.model.html#messages) with message history. |
| `events` | Optional. List of [Event](https://inspect.aisi.org.uk/reference/inspect_ai.event.html) with event history (e.g. model events, tool events, etc.) |

### Metadata

You can include arbitrary other fields in your database which will be
made available as `Transcript.metadata`. These fields can then be used
for filtering in calls to `Transcripts.where()`.

Note that `metadata` columns are forwarded into the results database for
scans (`transcript_metadata`) so it is generally a good practice to not
include large amounts of data in these columns.

### Messages

The `messages` field is a JSON encoded string of `list[ChatMessage]`.
There are several helper functions available within the `inspect_ai`
package to assist in converting from the raw message formats of various
providers to the Inspect `ChatMessage` format:

[TABLE]

For many straightforward transcripts the list of `messages` will be all
that is needed for analysis.

## Events

The `events` field is a JSON encoded string of `list[Event]`. Note that
if your scanners deal entirely in `messages` rather than `events` (as a
great many do) then it is not necessary to provide events.

Events are typically important when you are either analyzing complex
multi-agent transcripts or doing very granular scanning for specific
phenomena (e.g. tool calling errors).

While you can include any of the event types in defined in
[inspect_ai.event](https://inspect.aisi.org.uk/reference/inspect_ai.event.html),
there is a subset that is both likely to be of interest and that maps on
to data provided by observability platforms and/or OTEL traces. These
include:

| Event | Description |
|----|----|
| [ModelEvent](https://inspect.aisi.org.uk/reference/inspect_ai.event.html#modelevent) | Generation call to a model. |
| [ToolEvent](https://inspect.aisi.org.uk/reference/inspect_ai.event.html#toolevent) | Tool call made by a model. |
| [ErrorEvent](https://inspect.aisi.org.uk/reference/inspect_ai.event.html#errorevent) | Runtime error aborting transcript. |
| [SpanBeginEvent](https://inspect.aisi.org.uk/reference/inspect_ai.event.html#spanbeginevent) | Mark the beginning of a transcript span (e.g. agent execution, tool call, custom block, etc.) |
| [SpanEndEvent](https://inspect.aisi.org.uk/reference/inspect_ai.event.html#spanendevent) | Mark the end of a transcript scan |

Most observability systems will have some equivalent of the above in
their traces. When reconstructing model events you will also likely want
to use the helper functions mentioned above in [Messages](#messages) for
converting raw model API payloads to `ChatMessage`.

> [!NOTE]
>
> ### Not Required
>
> The `events` field is only important if you have scanners that will be
> doing event analysis. Note that the default `llm_scanner()` provided
> within Scout looks only at `messages` not `events`.
