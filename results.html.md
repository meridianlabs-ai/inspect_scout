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
  results (one for each scanner). There are functions available to
  interface with these files as Pandas data frames or DuckDB databases.

## Workflow

### Scout CLI

The `scout scan` command will print its status at the end of its run. If
all of the scanners completed without errors you’ll see a message
indicating the scan is complete along with a pointer to the scan
directory where results are stored:

![](images/scan-complete.png)

You can then pass that directory to the `scan_results()` function to get
access to the underlying data frames for each scanner:

``` python
from inspect_scout import scan_results

results = scan_results("scans/scan_id=3ibJe9cg7eM5zo3h5Hpbr8")
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
    scan, scan_results, transcripts_from_logs
)

from .scanners import ctf_environment, java_tool_calls

status = scan(
    transcripts=transcripts_from_logs("./logs"),
    scanners=[ctf_environment(), java_tool_calls()]
)

if status.complete:
    results = scan_results(status.location)
    deception_df = results.scanners["deception"]
    tool_errors_df = results.scanners["tool_errors"]
```

### DuckDB

The above examples demonstrated reading scanner output as Pandas data
frames. If you prefer, you can also read scanner data from a DuckDB
database as follows:

``` python
results = scan_results_db("scans/scan_id=3ibJe9cg7eM5zo3h5Hpbr8")
with results:
    # run queries to read data frames
    df = results.conn.execute("SELECT ...").fetch_df()

    # export entire database as file
    results.to_file("results.duckdb")
```

## Results Data

The `Results` object returned from `scan_results()` includes both
metadata about the scan as well as the scanner data frames:

| Field | Type | Description |
|----|----|----|
| `complete` | bool | Is the job complete? (all transcripts scanned) |
| `spec` | ScanSpec | Scan specification (transcripts, scanners, options, etc.) |
| `location` | str | Location of scan directory |
| `summary` | Summary | Summary of scan (results, errors, tokens, etc.) |
| `errors` | list\[Error\] | Errors during last scan attempt. |
| `scanners` | dict\[str, pd.DataFrame\] | Results data for each scanner (see [Data Frames](#scanner-data) for details) |

### Data Frames

<style type="text/css">
#scanner-data td:nth-child(2) {
  font-size: 0.9em;
  line-height: 1.2;
}
#scanner-data small {
  font-size: x-small;
}
</style>

The data frames available for each scanner contain information about the
source evaluation and transcript, the results found for each transcript,
as well as data on token usage, model calls, and errors which may have
occurred during the scan.

The data frame includes the following fields (note that some fields
included embedded JSON data, these are all noted below):

[TABLE]
