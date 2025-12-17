# Results


## Overview

The results of scans are stored in directory on the local filesystem (by
default `./scans`) or in a remote S3 bucket. When a scan job is
completed its directory is printed, and you can also use the
`scan_list()` function or `scout scan list` command to enumerate scan
jobs.

Scan results include the following:

- Scan configuration (e.g. options passed to `scan()` or to
  `scout scan`).

- Transcripts scanned and scanners executed and errors which occurred
  during the last scan.

- A set of [Parquet](https://parquet.apache.org/docs/) files with scan
  results (one for each scanner). Functions are available to interface
  with these files as Pandas data frames.

## Workflow

### Scout CLI

The `scout scan` command will print its status at the end of its run. If
all of the scanners completed without errors you’ll see a message
indicating the scan is complete along with a pointer to the scan
directory where results are stored:

![](images/scan-complete.png)

If you are running in VS Code, you can click the scan directory to view
the results in Scout View. If you are using another editor, execute
`scout view` from the terminal to launch the viewer:

``` bash
scout view
```

![](images/scout-view.png)

To get programmatic access to the results, pass the scan directory to
the `scan_results_df()` function:

``` python
from inspect_scout import scan_results_df

results = scan_results_df("scans/scan_id=3ibJe9cg7eM5zo3h5Hpbr8")
deception_df = results.scanners["deception"]
tool_errors_df = results.scanners["tool_errors"]
```

### Python API

The `scan()` function returns a `Status` object which indicates whether
the scan completed successfully (in which case the scanner results are
available for analysis). You’ll therefore want to check the `.completed`
field before proceeding to read the results. For example:

``` python
from inspect_scout import (
    scan, scan_results, transcripts_from
)

from .scanners import ctf_environment, java_tool_calls

status = scan(
    transcripts=transcripts_from("./logs"),
    scanners=[ctf_environment(), java_tool_calls()]
)

if status.complete:
    results = scan_results_df(status.location)
    deception_df = results.scanners["deception"]
    tool_errors_df = results.scanners["tool_errors"]
```

## Results Data

The `Results` object returned from `scan_results_df()` includes both
metadata about the scan as well as the scanner data frames:

| Field | Type | Description |
|----|----|----|
| `complete` | bool | Is the job complete? (all transcripts scanned) |
| `spec` | ScanSpec | Scan specification (transcripts, scanners, options, etc.) |
| `location` | str | Location of scan directory |
| `summary` | Summary | Summary of scan (results, metrics, errors, tokens, etc.) |
| `errors` | list\[Error\] | Errors during last scan attempt. |
| `scanners` | dict\[str, pd.DataFrame\] | Results data for each scanner (see [Data Frames](#data-frames) for details) |

### Data Frames

<style type="text/css">
#data-frames td:nth-child(2) {
  font-size: 0.9em;
  line-height: 1.2;
}
#data-frames small {
  font-size: x-small;
}
</style>

The data frames available for each scanner contain information about the
source evaluation and transcript, the results found for each transcript,
as well as model calls, errors and other events which may have occurred
during the scan.

#### Row Granularity

Note that by default the results data frame will include an individual
row for each result returned by a scanner. This means that if a scanner
returned [multiple results](scanners.qmd#multiple-results) there would
be multiple rows all sharing the same `transcript_id`. You can customize
this behavior via the `rows` option of the scan results functions:

|  |  |
|----|----|
| `rows = "results"` | Default. Yield a row for each scanner result (potentially multiple rows per transcript) |
| `rows = "transcripts"` | Yield a row for each transcript (in which case multiple results will be packed into the `value` field as a JSON list of `Result`) and the `value_type` will be “resultset”. |

#### Available Fields

The data frame includes the following fields (note that some fields
included embedded JSON data, these are all noted below):

| Field | Type | Description |
|----|----|----|
| `transcript_id` | str | Globally unique identifier for a transcript (e.g. sample `uuid` in the Inspect log). |
| `transcript_source_type` | str | Type of transcript source (e.g. “eval_log”). |
| `transcript_source_id` | str | Globally unique identifier for a transcript source (maps to `eval_id` in the Inspect log and analysis data frames). |
| `transcript_source_uri` | str | URI for source data (e.g. full path to the Inspect log file). |
| `transcript_date` | str | ISO 8601 datetime when the transcript was created. |
| `transcript_task_set` | str | Set from which transcript task was drawn (e.g. Inspect task name or benchmark name) |
| `transcript_task_id` | str | Identifier for task (e.g. dataset sample id). |
| `transcript_task_repeat` | int | Repeat for a given task id within a task set (e.g. epoch). |
| `transcript_agent` | str | Agent used to to execute task. |
| `transcript_agent_args` | dict JSON | Arguments passed to create agent. |
| `transcript_model` | str | Main model used by agent. |
| `transcript_score` | JsonValueJSON | Value indicating score on task. |
| `transcript_success` | bool | Boolean reduction of `score` to succeeded/failed. |
| `transcript_total_time` | number | Time required to execute task (seconds) |
| `transcript_total_tokens` | number | Tokens spent in execution of task. |
| `transcript_error` | str | Error message that terminated the task. |
| `transcript_limit` | str | Limit that caused the task to exit (e.g. “tokens”, “messages, etc.) |
| `transcript_metadata` | dict JSON | Source specific metadata. |
| `scan_id` | str | Globally unique identifier for scan. |
| `scan_tags` | list\[str\]JSON | Tags associated with the scan. |
| `scan_metadata` | dictJSON | Additional scan metadata. |
| `scan_git_origin` | str | Git origin for repo where scan was run from. |
| `scan_git_version` | str | Git version (based on tags) for repo where scan was run from. |
| `scan_git_commit` | str | Git commit for repo where scan was run from. |
| `scanner_key` | str | Unique key for scan within scan job (defaults to `scanner_name`). |
| `scanner_name` | str | Scanner name. |
| `scanner_version` | int | Scanner version. |
| `scanner_package_version` | int | Scanner package version. |
| `scanner_file` | str | Source file for scanner. |
| `scanner_params` | dictJSON | Params used to create scanner. |
| `input_type` | transcript \| message \| messages \| event \| events | Input type received by scanner. |
| `input_ids` | list\[str\]JSON | Unique ids of scanner input. |
| `input` | ScannerInputJSON | Scanner input value. |
| `uuid` | str | Globally unique id for scan result. |
| `label` | str | Label for the origin of the result (optional). |
| `value` | JsonValueJSON | Value returned by scanner. |
| `value_type` | string \| boolean \| number \| array \| object \| null | Type of value returned by scanner. |
| `answer` | str | Answer extracted from scanner generation. |
| `explanation` | str | Explanation for scan result. |
| `metadata` | dictJSON | Metadata for scan result. |
| `message_references` | list\[Reference\]JSON | Messages referenced by scanner. |
| `event_references` | list\[Reference\]JSON | Events referenced by scanner. |
| `validation_target` | JsonValueJSON | Target value from validation set. |
| `validation_result` | JsonValueJSON | Result returned from comparing `validation_target` to `value`. |
| `scan_error` | str | Error which occurred during scan. |
| `scan_error_traceback` | str | Traceback for error (if any) |
| `scan_error_type` | str | Error type (either “refusal” for refusals or null for other errors). |
| `scan_events` | list\[Event\]JSON | Scan events (e.g. model event, log event, etc.) |
| `scan_total_tokens` | number | Total tokens used by scan (only included when `rows = "transcripts"`). |
| `scan_model_usage` | dict \[str, ModelUsage\]JSON | Token usage by model for scan (only included when `rows = "transcripts"`). |

> [!NOTE]
>
> Note that the `transcript_*` fields are available only in the
> development version of Inspect Scout. Install the development version
> from GitHub with:
>
> ``` python
> pip install git+https://github.com/meridianlabs-ai/inspect_scout
> ```
