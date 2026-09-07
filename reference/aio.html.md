# Async API – Inspect Scout

> **NOTE: Note**
>
> The Async API is available for async programs that want to use `inspect_scout` as an embedded library.
>
> Normal usage of Scout (e.g. in a script or notebook) should prefer the corresponding sync functions (e.g. [scan()](../reference/scanning.html.md#scan), `scan_resume().`, etc.). This will provide optimal parallelism (sharing transcript parses across scanners, using multiple processes, etc.) compared to multiple concurrent calls to [scan_async()](../reference/aio.html.md#scan_async) (as in that case you would lose the pooled transcript parsing and create unwanted resource contention).

### scan_async

Scan transcripts.

Scan transcripts using one or more scanners. Note that scanners must each have a unique name. If you have more than one instance of a scanner with the same name, numbered prefixes will be automatically assigned. Alternatively, you can pass tuples of (name,scanner) or a dict with explicit names for each scanner.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/bef39729ae3a66084571cac3523e942d3feae561/src/inspect_scout/_scan.py#L192)

``` python
def scan_async(
    scanners: Scanners,
    transcripts: Transcripts | None = ...,
    scans: str | None = ...,
    worklist: Sequence[ScannerWork] | Sequence[Worklist] | str | Path | None = ...,
    validation: str | ValidationSet | Mapping[str, str | ValidationSet] | None = ...,
    model: str | Model | None = ...,
    model_config: GenerateConfig | None = ...,
    model_base_url: str | None = ...,
    model_args: dict[str, Any] | str | None = ...,
    model_roles: ModelRoles | None = ...,
    max_transcripts: int | None = ...,
    max_processes: int | None = ...,
    limit: int | None = ...,
    shuffle: bool | int | None = ...,
    results_buffer: int | None = ...,
    tags: list[str] | None = ...,
    metadata: dict[str, Any] | None = ...,
    log_level: str | None = ...,
    fail_on_error: bool = ...,
    dry_run: bool = ...,
    *,
    results: str | None = ...,
) -> Status
```

`scanners` [Scanners](../reference/scanner.html.md#scanners)  
Scanners to execute (list, dict with explicit names, or ScanJob). If a [ScanJob](../reference/scanning.html.md#scanjob) or [ScanJobConfig](../reference/scanning.html.md#scanjobconfig) is specified, then its options are used as the default options for the scan.

`transcripts` [Transcripts](../reference/transcript.html.md#transcripts) \| None  
Transcripts to scan.

`scans` str \| None  
Location to write results (filesystem or S3 bucket). Defaults to “./scans”.

`worklist` Sequence\[[ScannerWork](../reference/scanning.html.md#scannerwork)\] \| Sequence\[[Worklist](../reference/scanning.html.md#worklist)\] \| str \| Path \| None  
Transcript ids to process for each scanner (defaults to processing all transcripts). Either a list of [ScannerWork](../reference/scanning.html.md#scannerwork) or a YAML or JSON file contianing the same.

`validation` str \| [ValidationSet](../reference/results.html.md#validationset) \| Mapping\[str, str \| [ValidationSet](../reference/results.html.md#validationset)\] \| None  
Validation cases to apply for scanners. Can be a file path (CSV, JSON, JSONL, YAML), a ValidationSet, or a dict mapping scanner names to file paths or ValidationSets.

`model` str \| [Model](https://inspect.aisi.org.uk/reference/inspect_ai.model.html#model) \| None  
Model to use for scanning by default (individual scanners can always call [get_model()](https://inspect.aisi.org.uk/reference/inspect_ai.model.html#get_model) to us arbitrary models). If not specified use the model specified in the scout project config (if any).

`model_config` [GenerateConfig](https://inspect.aisi.org.uk/reference/inspect_ai.model.html#generateconfig) \| None  
`GenerationConfig` for calls to the model.

`model_base_url` str \| None  
Base URL for communicating with the model API.

`model_args` dict\[str, Any\] \| str \| None  
Model creation args (as a dictionary or as a path to a JSON or YAML config file).

`model_roles` [ModelRoles](https://inspect.aisi.org.uk/reference/inspect_ai.model.html#modelroles) \| None  
Named roles for use in [get_model()](https://inspect.aisi.org.uk/reference/inspect_ai.model.html#get_model).

`max_transcripts` int \| None  
The maximum number of transcripts to process concurrently (this also serves as the default value for `max_connections`). Defaults to 25.

`max_processes` int \| None  
The maximum number of concurrent processes (for multiproccesing). Defaults to 4.

`limit` int \| None  
Limit the number of transcripts processed.

`shuffle` bool \| int \| None  
Shuffle the order of transcripts (pass an `int` to set a seed for shuffling).

`results_buffer` int \| None  
Sync in-progress results to the scan location every N recorded results so they can be inspected while the scan is still running (defaults to None, which syncs results only on completion or interruption).

`tags` list\[str\] \| None  
One or more tags for this scan.

`metadata` dict\[str, Any\] \| None  
Metadata for this scan.

`log_level` str \| None  
Level for logging to the console: “debug”, “http”, “sandbox”, “info”, “warning”, “error”, “critical”, or “notset” (defaults to “warning”)

`fail_on_error` bool  
Re-raise exceptions instead of capturing them in results. Defaults to False.

`dry_run` bool  
Don’t actually run the scan, just print the spec and return the status. Defaults to False.

`results` str \| None  

### scan_resume_async

Resume a previous scan.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/bef39729ae3a66084571cac3523e942d3feae561/src/inspect_scout/_scan.py#L383)

``` python
async def scan_resume_async(
    scan_location: str,
    log_level: str | None = None,
    fail_on_error: bool = False,
    predicate_overrides: Mapping[str, PredicateFn] | None = None,
) -> Status
```

`scan_location` str  
Scan location to resume from.

`log_level` str \| None  
Level for logging to the console: “debug”, “http”, “sandbox”, “info”, “warning”, “error”, “critical”, or “notset” (defaults to “warning”)

`fail_on_error` bool  
Re-raise exceptions instead of capturing them in results.

`predicate_overrides` Mapping\[str, [PredicateFn](../reference/results.html.md#predicatefn)\] \| None  
Trusted custom validation predicates keyed by scanner name. Required when the portable scan spec cannot recreate a predicate.

### scan_complete_async

Complete a scan.

This function is used to indicate that a scan with errors in some transcripts should be completed in spite of the errors.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/bef39729ae3a66084571cac3523e942d3feae561/src/inspect_scout/_scan.py#L456)

``` python
async def scan_complete_async(
    scan_location: str, log_level: str | None = None
) -> Status
```

`scan_location` str  
Scan location to complete.

`log_level` str \| None  
Level for logging to the console: “debug”, “http”, “sandbox”, “info”, “warning”, “error”, “critical”, or “notset” (defaults to “warning”)

### scan_list_async

List completed and pending scans.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/bef39729ae3a66084571cac3523e942d3feae561/src/inspect_scout/_scanlist.py#L19)

``` python
async def scan_list_async(scans_location: str) -> list[Status]
```

`scans_location` str  
Location of scans to list.

### scan_status_async

Status of scan.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/bef39729ae3a66084571cac3523e942d3feae561/src/inspect_scout/_scanresults.py#L35)

``` python
async def scan_status_async(scan_location: str) -> Status
```

`scan_location` str  
Location to get status for (e.g. directory or s3 bucket)

### scan_results_df_async

Scan results as Pandas data frames.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/bef39729ae3a66084571cac3523e942d3feae561/src/inspect_scout/_scanresults.py#L109)

``` python
async def scan_results_df_async(
    scan_location: str,
    *,
    scanner: str | None = None,
    rows: Literal["results", "transcripts"] = "results",
    exclude_columns: Sequence[str] | None = None,
) -> ScanResultsDF
```

`scan_location` str  
Location of scan (e.g. directory or s3 bucket).

`scanner` str \| None  
Scanner name (defaults to all scanners).

`rows` Literal\['results', 'transcripts'\]  
Row granularity. Specify “results” to yield a row for each scanner result (potentially multiple per transcript); Specify “transcript” to yield a row for each transcript (in which case multiple results will be packed into the `value` field as a JSON list of [Result](../reference/scanner.html.md#result)).

`exclude_columns` Sequence\[str\] \| None  
Column names to exclude when reading parquet files. Defaults to `None`, which excludes the heavy columns (`input`, `input_data`, and `scan_events`, available as [HEAVY_COLUMNS](../reference/results.html.md#heavy_columns)) that dominate file size and memory usage. Pass `[]` to include all columns, or an explicit sequence to exclude exactly those columns. Use [scan_results_arrow()](../reference/results.html.md#scan_results_arrow) field accessors for per-row access to heavy columns.

### scan_results_arrow_async

Scan results as Arrow.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/bef39729ae3a66084571cac3523e942d3feae561/src/inspect_scout/_scanresults.py#L62)

``` python
async def scan_results_arrow_async(scan_location: str) -> ScanResultsArrow
```

`scan_location` str  
Location of scan (e.g. directory or s3 bucket).

### scan_results_batches_async

Stream a scanner’s results as pandas DataFrame batches.

Async variant of [scan_results_batches()](../reference/results.html.md#scan_results_batches): each batch (synchronous parquet I/O and pandas conversion) is pulled in a worker thread so the event loop is not blocked.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/bef39729ae3a66084571cac3523e942d3feae561/src/inspect_scout/_scanresults.py#L221)

``` python
async def scan_results_batches_async(
    scan_location: str,
    scanner: str,
    *,
    batch_size: int = 1024,
    exclude_columns: Sequence[str] | None = None,
    rows: Literal["results", "transcripts"] = "results",
) -> AsyncIterator[pd.DataFrame]
```

`scan_location` str  
Location of scan (e.g. directory or s3 bucket).

`scanner` str  
Scanner name.

`batch_size` int  
Maximum number of parquet rows read per batch (note that resultset expansion can yield more than `batch_size` rows per batch).

`exclude_columns` Sequence\[str\] \| None  
Column names to exclude when reading parquet files. Defaults to `None`, which excludes the heavy columns (`input`, `input_data`, and `scan_events`, available as [HEAVY_COLUMNS](../reference/results.html.md#heavy_columns)) that dominate file size and memory usage. Pass `[]` to include all columns, or an explicit sequence to exclude exactly those columns. Use [scan_results_arrow()](../reference/results.html.md#scan_results_arrow) field accessors for per-row access to heavy columns.

`rows` Literal\['results', 'transcripts'\]  
Row granularity. Specify “results” to yield a row for each scanner result (potentially multiple per transcript); Specify “transcript” to yield a row for each transcript (in which case multiple results will be packed into the `value` field as a JSON list of [Result](../reference/scanner.html.md#result)).
