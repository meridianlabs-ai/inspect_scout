# Database Schema


## Overview

In a transcript database, the only strictly required field is
`transcript_id` (although you’ll almost always want to also include a
`messages` field as that’s the main thing targeted by most scanners).

Further, there are many standard fields (e.g. `task`, `agent`, `model`,
`score`) which you’ll want to populate if you have access to them (as
this will provide important context both when viewing transcripts and
when viewing scan results). You can also include `source_*` fields as a
reference to where the transcript originated,. Finally, arbitrary other
fields can be included. All fields are queryable using the `Transcripts`
API.

Field types marked with (JSON) are stored in the database as serialized
JSON strings and then converted to richer types when accessed via the
`Transcript` interface.

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

### Events

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

## Schema in Code

> [!NOTE]
>
> Note that the programmatic access to schema described below is
> available only in the development version of Inspect Scout. Install
> the development version from GitHub with:
>
> ``` python
> pip install git+https://github.com/meridianlabs-ai/inspect_scout
> ```

If you are creating transcript databases outside of the Python
`TranscriptsDB.insert()` API, you can access the schema programmatically
or via the CLI.

### Python API

``` python
from inspect_scout import transcripts_db_schema

# Get PyArrow schema for creating Parquet files
schema = transcripts_db_schema(format="pyarrow")

# Create empty DataFrame with correct types
df = transcripts_db_schema(format="pandas")

# Get Avro schema
avro_schema = transcripts_db_schema(format="avro")

# Get JSON Schema
json_schema = transcripts_db_schema(format="json")
```

### CLI Commands

``` bash
# Print Avro schema
scout db schema --format avro

# Print PyArrow schema
scout db schema --format pyarrow

# Save schema to file
scout db schema --format avro --output transcript.avsc

# Validate a database schema
scout db validate ./my_transcript_db
```

## Importing Data

Now that you understand the schema and have an idea for how you want to
map your data into it, use one of the following methods to create the
database:

1.  [Transcript API](db_importing.qmd#transcript-api): Read and parse
    transcripts into `Transcript` objects and use the
    `TranscriptsDB.insert()` function to add them to the database.

2.  [Arrow Import](db_importing.qmd#arrow-import): Read an existing set
    of transcripts stored in Arrow/Parquet and pass them to
    `TranscriptsDB.insert()` as a PyArrow `RecordBatchReader`.

3.  [Parquet Data Lake](db_importing.qmd#parquet-data-lake): Point the
    `TranscriptDB` at an existing data lake (ensuring that the records
    adhere to the transcript database schema).

4.  [Inspect Logs](db_importing.qmd#inspect-logs): Import Inspect AI
    eval logs from a log directory.
