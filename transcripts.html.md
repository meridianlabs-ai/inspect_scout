# Transcripts


## Overview

Transcripts are the fundamental input to scanners. The `Transcripts`
class represents a collection of transcripts that has been selected for
scanning, and supports various filtering operations to refine the
collection.

## Reading Transcripts

Use the `transcripts_from()` function to read a collection of
`Transcripts`:

``` python
from inspect_scout import transcripts_from

# read from a transcript database on S3
transcripts = transcripts_from("s3://weave-rollouts/cybench")

# read from an Inspect log directory
transcripts = transcripts_from("./logs")
```

The `transcripts_from()` function can read transcripts from either:

1.  A transcript database that contains transcripts you have imported
    from a variety of sources (Agent traces, RL rollouts, Inspect logs,
    etc.); or

2.  One or more Inspect log directories that contain Inspect `.eval`
    logs.

See the sections below on the [Transcripts
Database](#transcripts-database) and [Inspect Eval
Logs](#inspect-eval-logs) for additional details on working with each.

## Filtering Transcripts

If you want to scan only a subset of transcripts, you can use the
`.where()` method to narrow down the collection. For example:

``` python
from inspect_scout import transcripts_from, metadata as m

transcripts = (
    transcripts_from("./logs")
    .where(m.task_name == "cybench")
    .where(m.model.like("openai/%"))
)
```

See the `Column` documentation for additional details on supported
filtering operations.

You can also limit the total number of transcripts as well as shuffle
the order of transcripts read (both are useful during scanner
development when you don’t want to process all transcripts). For
example:

``` python
from inspect_scout import transcripts_from, log_metadata as m

transcripts = (
    transcripts_from("./logs")
    .limit(10)
    .shuffle(42)
)
```

## Transcript Fields

Here are the available `Transcript` fields:

| Field | Type | Description |
|----|----|----|
| `transcript_id` | str | Globally unique identifier for a transcript (maps to `EvalSample.uuid` in Inspect logs). |
| `source_type` | str | Type of transcript source (e.g. “eval_log”, “weave”, etc.). |
| `source_id` | str | Globally unique identifier for a transcript source (maps to `eval_id` in Inspect logs) |
| `source_uri` | str | URI for source data (e.g. full path to the Inspect log file). |
| `metadata` | dict\[str, JsonValue\] | Transcript source specific metadata (e.g. model, task name, errors, epoch, dataset sample id, limits, etc.). |
| `messages` | [list\[ChatMessage\]](https://inspect.aisi.org.uk/reference/inspect_ai.model.html#messages) | Message history. |
| `events` | [list\[Event\]](https://inspect.aisi.org.uk/reference/inspect_ai.event.html) | Event history (e.g. model events, tool events, etc.) |

## Scanning Transcripts

Once you have established your list of transcripts to scan, just pass
them to the `scan()` function:

``` python
from inspect_scout import scan, transcripts_from

from .scanners import ctf_environment, java_tool_calls

scan(
    scanners = [ctf_environment(), java_tool_calls()],
    transcripts = transcripts_from("./logs")
)
```

If you want to do transcript filtering and then invoke your scan from
the CLI using `scout scan`, then perform the filtering inside a
`@scanjob`. For example:

**cybench_scan.py**

``` python
from inspect_scout (
    import ScanJob, scanjob, transcripts_from, metadata as m
)

from .scanners import deception, tool_errors

@scanjob
def cybench_job(logs: str = "./logs") -> ScanJob:

    transcripts = transcripts_from(logs)
    transcripts = transcripts.where(m.task_name == "cybench")

    return ScanJob(
        scanners = [deception(), java_tool_usages()],
        transcripts = transcripts
    )
```

Then from the CLI:

``` bash
scout scan cybench.py -S logs=./logs --model openai/gpt-5
```

The `-S` argument enables you to pass arguments to the `@scanjob`
function (in this case determining what directory to read logs from).

## Inspect Eval Logs

The `transcripts_from()` function can read a collection of transcripts
directly from an Inspect log directory. You can specify one or more
directories and/or individual log files. For example:

``` python
# read from a log directory
transcripts = transcripts_from("./logs")

# read multiple log directories
transcripts = transcripts_from(["./logs", "./logs2"])

# read from one or more log files
transcripts = transcripts_from(
    ["logs/cybench.eval", "logs/swebench.eval"]
)
```

For Inspect logs, the `metadata` field within `TranscriptInfo` includes
fields from eval sample metadata. For example:

``` python
transcript.metadata["sample_id"]        # sample uuid 
transcript.metadata["id"]               # dataset sample id 
transcript.metadata["epoch"]            # sample epoch
transcript.metadata["eval_metadata"]    # eval metadata
transcript.metadata["sample_metadata"]  # sample metadata
transcript.metadata["score"]            # main sample score 
transcript.metadata["score_<scorer>"]   # named sample scores
```

See the `LogMetadata` class for details on all of the fields included in
`transcript.metadata`. Use `log_metadata` (aliased to `m` below) to do
typesafe filtering for Inspect logs:

``` python
from inspect_scout import transcripts_from, log_metadata as m

transcripts = (
    transcripts_from("./logs")
    .where(m.task_name == "cybench")
    .where(m.model.like("openai/%"))
)
```

## Transcripts Database

Scout can analyze transcripts from any source (e.g. Agent traces, RL
rollouts, etc.) so long as the transcripts have been imported into a
transcripts database. Transcript databases use
[Parquet](https://parquet.apache.org) files for storage and can be
located in the local filesystem or remote systems like S3.

To create a transcripts database, use the `transcripts_db()` function to
get a `TranscriptsDB` interface and then insert `Transcript` objects. In
this example imagine we have a `read_weave_transcripts()` function which
can read transcripts from an external JSON transcript format:

``` python
from inspect_scout import transcripts_db

from .readers import read_json_transcripts

# create/open database
async with transcripts_db("s3://my-transcripts") as db:

    # read transcripts to insert
    transcripts = read_json_transcripts()

    # insert into database
    await db.insert(transcripts)
```

Once you’ve created a database and populated it with transcripts, you
can read from it using `transcripts_from()`:

``` python
from inspect_scout import scan, transcripts_from

scan(
    scanners=[...],
    transcripts=transcripts_from("s3://my-transcripts")
)
```

### Streaming

If you are inserting a large number of transcripts you will likely want
to read them in a generator that streams transcripts. For example, we
might implement `read_json_transcripts()` like this:

``` python

from pathlib import Path
from typing import AsyncIterator

async def read_json_transcripts(dir: Path) -> AsyncIterator[Transcript]:
    json_files = list(dir.rglob("*.json"))
    for json_file in json_files:
        yield json_to_transcript(json_file)

def json_to_transcript(json_file: Path) -> Transcript:
    # convert json_file to Transcript
    return Transcript(...)
```

We can then pass this generator function directly to `db.insert()`:

``` python
async with transcripts_db("s3://my-transcripts") as db:
    await db.insert(read_json_transcripts())
```

Note that transcript insertion is idempotent—once a transcript with a
given ID has been inserted it will not be inserted again. This means
that you can safely resume imports that are interrupted, and only new
transcripts will be added.

### Transcripts

Databases are composed of `Transcript` objects, which minimally have a
`transcript_id` and a list of `messages`. In addition, there are fields
you can include that indicate the *source* of the transcript and
metadata about transcript.

| Field | Description |
|----|----|
| `transcript_id` | Required. A globally unique identifier for a transcript. Provides a reference from the transcript database to the origin of the transcript. |
| `source_type` | Optional. Type of transcript source (e.g. “weave”, “logfire”, “eval_log”, etc.). Useful for providing a hint to readers about what might be available in the `metadata` field. |
| `source_id` | Optional. Globally unique identifier for a transcript source (e.g. a project id). |
| `source_uri` | Optional. URI for source data (e.g. link to a web page or REST resource for discovering more about the transcript). |
| `metadata` | Optional. Dict of source specific metadata (e.g. agent name, model, dataset, limits, scores, etc.). |
| `messages` | Optional. List of [ChatMessage](https://inspect.aisi.org.uk/reference/inspect_ai.model.html#messages) with message history. |
| `events` | Optional. List of [Event](https://inspect.aisi.org.uk/reference/inspect_ai.event.html) with event history (e.g. model events, tool events, etc.) |

For example, here is how we might implement `json_to_transcript()`:

``` python
def json_to_transcript(json_file: Path) -> Transcript:
    with open(json_file, "r") as f:
        json_data: dict[str,Any] = json.loads(f.read())
        return Transcript(
            transcript_id = json_data["trace_id"],
            source_type="abracadabra",
            source_id=json_data["project_id"],
            metadata=json_data["attributes"],
            messages=json_messages(json_data)
        )
    
def json_messages(json_data: dict[str, Any]) -> list[ChatMessage]:
    # extract chat messages from json_data
```

The most important fields to populate are `transcript_id` and
`messages`. The `source_*` fields are also useful for providing
additional context. The `metadata` field, while not required, is a
convenient way to provide additional transcript attributes which may be
useful for filtering or analysis. The `events` field is not required and
useful primarily for more complex multi-agent transcripts.

### Storage

Transcript databases are stored on a local or remote filesystem using
[Parquet](https://parquet.apache.org) files, which are optimized for
fast access to metadata and incremental access to larger content fields
(e.g. `messages` and `events`).

Each call to `db.insert()` will minimally create one Parquet file, but
will break transcripts across multiple files as required, limiting the
size of files to 100MB. This will create a storage layout optimized for
fast queries and content reading. Consequently, when importing a large
number of transcripts you should always write a generator (as shown
above), rather than making many calls to `db.insert()` (which is likely
to result in more Parquet files than is ideal).

### Importing Logs

If you prefer to keep all of your transcripts (including ones from
Inspect evals) in a transcript database, you can easily import Inspect
logs as follows:

``` python
from inspect_scout import transcripts_db, transcripts_from

async with transcripts_db("s3://my-transcript-db/") as db:
    await db.insert(transcripts_from("./logs"))
```

You could also insert a filtered list of transcripts:

``` python
async with transcripts_db("s3://my-transcript-db/") as db:

    transcripts = (
        transcripts_from("./logs")
        .where(m.task_name == "cybench")
        .where(m.model.like("openai/%"))
    )

    await db.insert(transcripts)
```
