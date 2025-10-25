# Async API


> [!NOTE]
>
> The Async API is available for async programs that want to use
> `inspect_scout` as an embedded library. Normal usage of Scout (e.g. in
> a script or notebook) should prefer the corresponding sync functions
> (e.g. `scan()`, `scan_resume().`, etc.)

### scan_async

Scan transcripts.

Scan transcripts using one or more scanners. Note that scanners must
each have a unique name. If you have more than one instance of a scanner
with the same name, numbered prefixes will be automatically assigned.
Alternatively, you can pass tuples of (name,scanner) or a dict with
explicit names for each scanner.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/aec46df092a5d6a7fdbc989f68637f8fe3cb17d8/src/inspect_scout/_scan.py#L139)

``` python
async def scan_async(
    scanners: Sequence[Scanner[ScannerInput] | tuple[str, Scanner[ScannerInput]]]
    | dict[str, Scanner[ScannerInput]]
    | ScanJob
    | ScanJobConfig,
    transcripts: Transcripts | None = None,
    results: str | None = None,
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
) -> Status
```

`scanners` Sequence\[[Scanner](scanner.qmd#scanner)\[[ScannerInput](scanner.qmd#scannerinput)\] \| tuple\[str, [Scanner](scanner.qmd#scanner)\[[ScannerInput](scanner.qmd#scannerinput)\]\]\] \| dict\[str, [Scanner](scanner.qmd#scanner)\[[ScannerInput](scanner.qmd#scannerinput)\]\] \| [ScanJob](scanning.qmd#scanjob) \| [ScanJobConfig](scanning.qmd#scanjobconfig)  
Scanners to execute (list, dict with explicit names, or ScanJob). If a
`ScanJob` or `ScanJobConfig` is specified, then its options are used as
the default options for the scan.

`transcripts` [Transcripts](transcript.qmd#transcripts) \| None  
Transcripts to scan.

`results` str \| None  
Location to write results (filesystem or S3 bucket). Defaults to
“./scans”.

`model` str \| Model \| None  
Model to use for scanning by default (individual scanners can always
call `get_model()` to us arbitrary models). If not specified use the
value of the SCOUT_SCAN_MODEL environment variable.

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
Defaults to `multiprocessing.cpu_count()`.

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

### scan_resume_async

Resume a previous scan.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/aec46df092a5d6a7fdbc989f68637f8fe3cb17d8/src/inspect_scout/_scan.py#L267)

``` python
async def scan_resume_async(scan_location: str, log_level: str | None = None) -> Status
```

`scan_location` str  
Scan location to resume from.

`log_level` str \| None  
Level for logging to the console: “debug”, “http”, “sandbox”, “info”,
“warning”, “error”, “critical”, or “notset” (defaults to “warning”)

### scan_complete_async

Complete a scan.

This function is used to indicate that a scan with errors in some
transcripts should be completed in spite of the errors.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/aec46df092a5d6a7fdbc989f68637f8fe3cb17d8/src/inspect_scout/_scan.py#L331)

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

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/aec46df092a5d6a7fdbc989f68637f8fe3cb17d8/src/inspect_scout/_scanlist.py#L19)

``` python
async def scan_list_async(scans_location: str) -> list[Status]
```

`scans_location` str  
Location of scans to list.

### scan_status_async

Status of scan.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/aec46df092a5d6a7fdbc989f68637f8fe3cb17d8/src/inspect_scout/_scanresults.py#L23)

``` python
async def scan_status_async(scan_location: str) -> Status
```

`scan_location` str  
Location to get status for (e.g. directory or s3 bucket)

### scan_results_async

Scan results as Pandas data frames.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/aec46df092a5d6a7fdbc989f68637f8fe3cb17d8/src/inspect_scout/_scanresults.py#L54)

``` python
async def scan_results_async(
    scan_location: str, *, scanner: str | None = None, include_null: bool = False
) -> Results
```

`scan_location` str  
Location of scan (e.g. directory or s3 bucket).

`scanner` str \| None  
Scanner name (defaults to all scanners).

`include_null` bool  
Should `None` results be included in the data frame (defaults to
`False`)

### scan_results_db_async

Scan results as DuckDB database.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/aec46df092a5d6a7fdbc989f68637f8fe3cb17d8/src/inspect_scout/_scanresults.py#L86)

``` python
async def scan_results_db_async(
    scan_location: str, include_null: bool = False
) -> ResultsDB
```

`scan_location` str  
Location of scan (e.g. directory or s3 bucket).

`include_null` bool  
Should `None` results be included in the data frame (defaults to
`False`)
