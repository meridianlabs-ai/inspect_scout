# Transcripts


## Overview

Transcripts are the fundamental input to scanners, and are read from one
or more Inspect logs. The `Transcripts` class represents a collection of
transcripts that has been selected for scanning. This is an index of
`TranscriptInfo` rather than full transcript content, and supports
various filtering operations to refine the collection.

## Reading Transcripts

Use the `transcripts_from_logs()` function to read a collection of
`Transcripts` from one or more Inspect logs:

``` python
from inspect_scout import transcripts_from_logs

# read from a log directory
transcripts = transcripts_from_logs("./logs")

# read from an S3 log directory
transcripts = transcripts_from_logs("s3://my-inspect-logs")

# read multiple log directories
transcripts = transcripts_from_logs(["./logs", "./logs2"])

# read from one or more log files
transcripts = transcripts_from_logs(
    ["logs/cybench.eval", "logs/swebench.eval"]
)
```

## Filtering Transcripts

If you want to scan only a subset of transcripts, you can use the
`.where()` method to narrow down the collection. For example:

``` python
from inspect_scout import transcripts_from_logs, log_metadata as m

transcripts = (
    transcripts_from_logs("./logs")
    .where(m.task_name == "cybench")
    .where(m.model.like("openai/%"))
)
```

See the `Column` documentation for additional details on supported
filtering operations.

See the `LogMetadata` documentation for the standard metadata fields
that are exposed from logs for filtering.

You can also limit the total number of transcripts as well as shuffle
the order of transcripts read (both are useful during scanner
development when you don’t want to process all transcripts). For
example:

``` python
from inspect_scout import transcripts_from_logs, log_metadata as m

transcripts = (
    transcripts_from_logs("./logs")
    .limit(10)
    .shuffle(42)
)
```

## Transcript Fields

The `Transcript` type is defined somewhat generally to accommodate other
non-Inspect transcript sources in the future. Here are the available
`Transcript` fields and how these map back onto Inspect logs:

| Field | Type | Description |
|----|----|----|
| `id` | str | Globally unique identifier for a transcript (maps to `EvalSample.uuid` in the Inspect log). |
| `source_id` | str | Globally unique identifier for a transcript source (maps to `eval_id` in the Inspect log) |
| `source_uri` | str | URI for source data (e.g. full path to the Inspect log file). |
| `score` | JsonValue | Main score assigned to transcript (optional). |
| `scores` | dict\[str, JsonValue\] | All scores assigned to transcript (optional). |
| `variables` | dict\[str, JsonValue\] | Variables (e.g. to be used in a prompt template) associated with transcript. For Inspect logs this is `Sample.metadata`. |
| `metadata` | dict\[str, JsonValue\] | Transcript source specific metadata (e.g. model, task name, errors, epoch, dataset sample id, limits, etc.). See `LogMetadata` for details on metadata available for Inspect logs. |
| `messages` | list\[ChatMessage\] | Message history from `EvalSample` |
| `events` | list\[Event\] | Event history from `EvalSample` |

The `metadata` field includes fields read from eval sample metadata. For
example:

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
`transcript.metadata` for Inspect logs.

## Scanning Transcripts

Once you have established your list of transcripts to scan, just pass
them to the `scan()` function:

``` python
from inspect_scout import scan, transcripts_from_logs

from .scanners import ctf_environment, java_tool_calls

scan(
    scanners = [ctf_environment(), java_tool_calls()],
    transcripts = transcripts_from_logs("./logs")
)
```

If you want to do transcript filtering and then invoke your scan from
the CLI using `scout scan`, then perform the filtering inside a
`@scanjob`. For example:
