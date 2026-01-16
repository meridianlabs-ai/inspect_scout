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
from inspect_scout import transcripts_from, columns as c

transcripts = (
    transcripts_from("./logs")
    .where(c.task_set == "cybench")
    .where(c.model.like("openai/%"))
)
```

See the `Columns` documentation for additional details on supported
filtering operations.

You can also limit the total number of transcripts as well as shuffle
the order of transcripts read (both are useful during scanner
development when you don’t want to process all transcripts). For
example:

``` python
from inspect_scout import transcripts_from

transcripts = (
    transcripts_from("./logs")
    .limit(10)
    .shuffle(42)
)
```

## Viewing Transcripts

You can use Scout View to view and filter transcripts:

![](images/transcripts-list.png)

If you filter down into a set of transcripts that you want to analyze,
use the **Copy** button to copy the code required to apply the filter:

![](images/transcripts-copy.png)

If you drill into a transcript you can see its messages, events, and
other details:

![](images/transcripts-detail.png)

## Transcript Fields

Here are the available `Transcript` fields:

| Field | Type | Description |
|----|----|----|
| `transcript_id` | str | Globally unique identifier for a transcript (maps to `EvalSample.uuid` in Inspect logs). |
| `source_type` | str | Type of transcript source (e.g. “eval_log”, “weave”, etc.). |
| `source_id` | str | Globally unique identifier for a transcript source (maps to `eval_id` in Inspect logs) |
| `source_uri` | str | URI for source data (e.g. full path to the Inspect log file). |
| `date` | iso | Date/time when the transcript was created. |
| `task_set` | str | Set from which transcript task was drawn (e.g. Inspect task name or benchmark name) |
| `task_id` | str | Identifier for task (e.g. dataset sample id). |
| `task_repeat` | int | Repeat for a given task id within a task set (e.g. epoch). |
| `agent` | str | Agent used to to execute task. |
| `agent_args` | dict JSON | Arguments passed to create agent. |
| `model` | str | Main model used by agent. |
| `model_options` | dict JSON | Generation options for main model. |
| `score` | JsonValueJSON | Value indicating score on task. |
| `success` | bool | Boolean reduction of `score` to succeeded/failed. |
| `total_time` | number | Time required to execute task (seconds) |
| `total_tokens` | number | Tokens spent in execution of task. |
| `error` | str | Error message that terminated the task. |
| `limit` | str | Limit that caused the task to exit (e.g. “tokens”, “messages, etc.) |
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
    import ScanJob, scanjob, transcripts_from, columns as c
)

from .scanners import deception, tool_errors

@scanjob
def cybench_job(logs: str = "./logs") -> ScanJob:

    transcripts = transcripts_from(logs)
    transcripts = transcripts.where(c.task_set == "cybench")

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
transcript.metadata["score_<scorer>"]   # named sample scores
```

See the `LogColumns` class for details on all of the fields included in
`transcript.metadata`. Use `log_columns` (aliased to `c` below) to do
typesafe filtering for Inspect logs:

``` python
from inspect_scout import transcripts_from, log_columns as c

transcripts = (
    transcripts_from("./logs")
    .where(c.sample_metadata.category == "accounting")
)
```

## Transcripts Database

Scout can analyze transcripts from any source (e.g. Agent traces, RL
rollouts, etc.) so long as the transcripts have been organized into a
transcripts database. Transcript databases use
[Parquet](https://parquet.apache.org) files for storage and can be
located in the local filesystem or remote systems like S3.

You can read from a transcript database using the `transcripts_from()`
function. For example:

``` python
from inspect_scout import transcripts_from

# read from a transcript database on S3
transcripts = transcripts_from("s3://weave-rollouts/cybench")
```

See the [Transcripts Database](db_overview.qmd) documentation for
additional details on creating, managing, and publishing transcript
databases.
