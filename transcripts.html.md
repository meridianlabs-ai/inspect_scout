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
