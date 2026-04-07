# Results

## Overview

The results of scans are stored in directory on the local filesystem (by default `./scans`) or in a remote S3 bucket. When a scan job is completed its directory is printed, and you can also use the [scan_list()](reference/results.html.md#scan_list) function or `scout scan list` command to enumerate scan jobs.

Scan results include the following:

- Scan configuration (e.g. options passed to [scan()](reference/scanning.html.md#scan) or to `scout scan`).

- Transcripts scanned and scanners executed and errors which occurred during the last scan.

- A set of [Parquet](https://parquet.apache.org/docs/) files with scan results (one for each scanner). Functions are available to interface with these files as Pandas data frames.

## Workflow

### Scout CLI

The `scout scan` command will print its status at the end of its run. If all of the scanners completed without errors you’ll see a message indicating the scan is complete along with a pointer to the scan directory where results are stored:

![](images/scan-complete.png)

If you are running in VS Code, you can click the scan directory to view the results in Scout View. If you are using another editor, execute `scout view` from the terminal to launch the viewer:

``` bash
scout view
```

![](images/scout-view.png)

To get programmatic access to the results, pass the scan directory to the [scan_results_df()](reference/results.html.md#scan_results_df) function:

``` python
from inspect_scout import scan_results_df

results = scan_results_df("scans/scan_id=3ibJe9cg7eM5zo3h5Hpbr8")
deception_df = results.scanners["deception"]
tool_errors_df = results.scanners["tool_errors"]
```

### Python API

The [scan()](reference/scanning.html.md#scan) function returns a [Status](reference/results.html.md#status) object which indicates whether the scan completed successfully (in which case the scanner results are available for analysis). You’ll therefore want to check the `.completed` field before proceeding to read the results. For example:

``` python
from inspect_scout import (
    scan, scan_results_df, transcripts_from
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

The `Results` object returned from [scan_results_df()](reference/results.html.md#scan_results_df) includes both metadata about the scan as well as the scanner data frames:

| Field | Type | Description |
|----|----|----|
| `complete` | bool | Is the job complete? (all transcripts scanned) |
| `spec` | ScanSpec | Scan specification (transcripts, scanners, options, etc.) |
| `location` | str | Location of scan directory |
| `summary` | Summary | Summary of scan (results, metrics, errors, tokens, etc.) |
| `errors` | list\[Error\] | Errors during last scan attempt. |
| `scanners` | dict\[str, pd.DataFrame\] | Results data for each scanner (see [Data Frames](#data-frames) for details) |

### Data Frames

The data frames available for each scanner contain information about the source evaluation and transcript, the results found for each transcript, as well as model calls, errors and other events which may have occurred during the scan.

#### Row Granularity

Note that by default the results data frame will include an individual row for each result returned by a scanner. This means that if a scanner returned [multiple results](scanners.html.md#multiple-results) there would be multiple rows all sharing the same `transcript_id`. You can customize this behavior via the `rows` option of the scan results functions:

|  |  |
|----|----|
| `rows = "results"` | Default. Yield a row for each scanner result (potentially multiple rows per transcript) |
| `rows = "transcripts"` | Yield a row for each transcript (in which case multiple results will be packed into the `value` field as a JSON list of [Result](reference/scanner.html.md#result)) and the `value_type` will be “resultset”. |

#### Available Fields

The data frame includes the following fields (note that some fields included embedded JSON data, these are all noted below):

[TABLE]
