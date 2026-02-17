# Async API


> [!NOTE]
>
> The Async API is available for async programs that want to use
> `inspect_scout` as an embedded library.
>
> Normal usage of Scout (e.g. in a script or notebook) should prefer the
> corresponding sync functions (e.g. `scan()`, `scan_resume().`, etc.).
> This will provide optimal parallelism (sharing transcript parses
> across scanners, using multiple processes, etc.) compared to multiple
> concurrent calls to `scan_async()` (as in that case you would lose the
> pooled transcript parsing and create unwanted resource contention).

### scan_async

Scan transcripts.

Scan transcripts using one or more scanners. Note that scanners must
each have a unique name. If you have more than one instance of a scanner
with the same name, numbered prefixes will be automatically assigned.
Alternatively, you can pass tuples of (name,scanner) or a dict with
explicit names for each scanner.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/c4c4b277aff6b425adccf372e9b85ada21ae73a1/src/inspect_scout/_scan.py#L184)

``` python
async def scan_async(
    scanners: (
        Sequence[Scanner[Any] | tuple[str, Scanner[Any]]]
        | dict[str, Scanner[Any]]
        | ScanJob
        | ScanJobConfig
    ),
    transcripts: Transcripts | None = None,
    scans: str | None = None,
    worklist: Sequence[ScannerWork] | Sequence[Worklist] | str | Path | None = None,
    validation: str | ValidationSet | Mapping[str, str | ValidationSet] | None = None,
    model: str | Model | None = None,
    model_config: GenerateConfig | None = None,
    model_base_url: str | None = None,
    model_args: dict[str, Any] | str | None = None,
    model_roles: dict[str, str | Model] | None = None,
    max_transcripts: int | None = None,
    max_processes: int | None = None,
    limit: int | None = None,
    shuffle: bool | int | None = None,
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
    log_level: str | None = None,
    fail_on_error: bool = False,
    dry_run: bool = False,
    **deprecated: Unpack[ScanDeprecatedArgs],
) -> Status
```

`scanners` Sequence\[[Scanner](scanner.qmd#scanner)\[Any\] \| tuple\[str, [Scanner](scanner.qmd#scanner)\[Any\]\]\] \| dict\[str, [Scanner](scanner.qmd#scanner)\[Any\]\] \| [ScanJob](scanning.qmd#scanjob) \| [ScanJobConfig](scanning.qmd#scanjobconfig)  
Scanners to execute (list, dict with explicit names, or ScanJob). If a
`ScanJob` or `ScanJobConfig` is specified, then its options are used as
the default options for the scan.

`transcripts` [Transcripts](transcript.qmd#transcripts) \| None  
Transcripts to scan.

`scans` str \| None  
Location to write results (filesystem or S3 bucket). Defaults to
“./scans”.

`worklist` Sequence\[[ScannerWork](scanning.qmd#scannerwork)\] \| Sequence\[[Worklist](scanning.qmd#worklist)\] \| str \| Path \| None  
Transcript ids to process for each scanner (defaults to processing all
transcripts). Either a list of `ScannerWork` or a YAML or JSON file
contianing the same.

`validation` str \| [ValidationSet](results.qmd#validationset) \| Mapping\[str, str \| [ValidationSet](results.qmd#validationset)\] \| None  
Validation cases to apply for scanners. Can be a file path (CSV, JSON,
JSONL, YAML), a ValidationSet, or a dict mapping scanner names to file
paths or ValidationSets.

`model` str \| Model \| None  
Model to use for scanning by default (individual scanners can always
call `get_model()` to us arbitrary models). If not specified use the
model specified in the scout project config (if any).

`model_config` GenerateConfig \| None  
`GenerationConfig` for calls to the model.

`model_base_url` str \| None  
Base URL for communicating with the model API.

`model_args` dict\[str, Any\] \| str \| None  
Model creation args (as a dictionary or as a path to a JSON or YAML
config file).

`model_roles` dict\[str, str \| Model\] \| None  
Named roles for use in `get_model()`.

`max_transcripts` int \| None  
The maximum number of transcripts to process concurrently (this also
serves as the default value for `max_connections`). Defaults to 25.

`max_processes` int \| None  
The maximum number of concurrent processes (for multiproccesing).
Defaults to 4.

`limit` int \| None  
Limit the number of transcripts processed.

`shuffle` bool \| int \| None  
Shuffle the order of transcripts (pass an `int` to set a seed for
shuffling).

`tags` list\[str\] \| None  
One or more tags for this scan.

`metadata` dict\[str, Any\] \| None  
Metadata for this scan.

`log_level` str \| None  
Level for logging to the console: “debug”, “http”, “sandbox”, “info”,
“warning”, “error”, “critical”, or “notset” (defaults to “warning”)

`fail_on_error` bool  
Re-raise exceptions instead of capturing them in results. Defaults to
False.

`dry_run` bool  
Don’t actually run the scan, just print the spec and return the status.
Defaults to False.

`**deprecated` Unpack\[ScanDeprecatedArgs\]  
Deprecated arguments.

### scan_resume_async

Resume a previous scan.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/c4c4b277aff6b425adccf372e9b85ada21ae73a1/src/inspect_scout/_scan.py#L369)

``` python
async def scan_resume_async(
    scan_location: str, log_level: str | None = None, fail_on_error: bool = False
) -> Status
```

`scan_location` str  
Scan location to resume from.

`log_level` str \| None  
Level for logging to the console: “debug”, “http”, “sandbox”, “info”,
“warning”, “error”, “critical”, or “notset” (defaults to “warning”)

`fail_on_error` bool  
Re-raise exceptions instead of capturing them in results.

### scan_complete_async

Complete a scan.

This function is used to indicate that a scan with errors in some
transcripts should be completed in spite of the errors.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/c4c4b277aff6b425adccf372e9b85ada21ae73a1/src/inspect_scout/_scan.py#L437)

``` python
async def scan_complete_async(
    scan_location: str, log_level: str | None = None
) -> Status
```

`scan_location` str  
Scan location to complete.

`log_level` str \| None  
Level for logging to the console: “debug”, “http”, “sandbox”, “info”,
“warning”, “error”, “critical”, or “notset” (defaults to “warning”)

### scan_list_async

List completed and pending scans.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/c4c4b277aff6b425adccf372e9b85ada21ae73a1/src/inspect_scout/_scanlist.py#L19)

``` python
async def scan_list_async(scans_location: str) -> list[Status]
```

`scans_location` str  
Location of scans to list.

### scan_status_async

Status of scan.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/c4c4b277aff6b425adccf372e9b85ada21ae73a1/src/inspect_scout/_scanresults.py#L31)

``` python
async def scan_status_async(scan_location: str) -> Status
```

`scan_location` str  
Location to get status for (e.g. directory or s3 bucket)

### scan_results_df_async

Scan results as Pandas data frames.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/c4c4b277aff6b425adccf372e9b85ada21ae73a1/src/inspect_scout/_scanresults.py#L100)

``` python
async def scan_results_df_async(
    scan_location: str,
    *,
    scanner: str | None = None,
    rows: Literal["results", "transcripts"] = "results",
    exclude_columns: list[str] | None = None,
) -> ScanResultsDF
```

`scan_location` str  
Location of scan (e.g. directory or s3 bucket).

`scanner` str \| None  
Scanner name (defaults to all scanners).

`rows` Literal\['results', 'transcripts'\]  
Row granularity. Specify “results” to yield a row for each scanner
result (potentially multiple per transcript); Specify “transcript” to
yield a row for each transcript (in which case multiple results will be
packed into the `value` field as a JSON list of `Result`).

`exclude_columns` list\[str\] \| None  
List of column names to exclude when reading parquet files. Useful for
reducing memory usage by skipping large unused columns.

### scan_results_arrow_async

Scan results as Arrow.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/c4c4b277aff6b425adccf372e9b85ada21ae73a1/src/inspect_scout/_scanresults.py#L58)

``` python
async def scan_results_arrow_async(scan_location: str) -> ScanResultsArrow
```

`scan_location` str  
Location of scan (e.g. directory or s3 bucket).
