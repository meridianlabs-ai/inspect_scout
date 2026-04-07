# Scanning

Running scans, configuring jobs, and orchestrating multi-scanner runs.

## Scanning

### scan

Scan transcripts.

Scan transcripts using one or more scanners. Note that scanners must each have a unique name. If you have more than one instance of a scanner with the same name, numbered prefixes will be automatically assigned. Alternatively, you can pass tuples of (name,scanner) or a dict with explicit names for each scanner.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/5282cf41f9ae85a8bc81a91585c6c3424508c536/src/inspect_scout/_scan.py#L90)

``` python
def scan(
    scanners: Sequence[Scanner[Any] | tuple[str, Scanner[Any]]] | dict[str, Scanner[Any]] | ScanJob | ScanJobConfig,
    transcripts: Transcripts | None = ...,
    scans: str | None = ...,
    worklist: Sequence[ScannerWork] | Sequence[Worklist] | str | Path | None = ...,
    validation: str | ValidationSet | Mapping[str, str | ValidationSet] | None = ...,
    model: str | Model | None = ...,
    model_config: GenerateConfig | None = ...,
    model_base_url: str | None = ...,
    model_args: dict[str, Any] | str | None = ...,
    model_roles: dict[str, str | Model] | None = ...,
    max_transcripts: int | None = ...,
    max_processes: int | None = ...,
    limit: int | None = ...,
    shuffle: bool | int | None = ...,
    tags: list[str] | None = ...,
    metadata: dict[str, Any] | None = ...,
    display: DisplayType | None = ...,
    log_level: str | None = ...,
    fail_on_error: bool = ...,
    dry_run: bool = ...,
    *,
    results: str | None = ...,
) -> Status
```

`scanners` Sequence\[[Scanner](../reference/scanner.html.md#scanner)\[Any\] \| tuple\[str, [Scanner](../reference/scanner.html.md#scanner)\[Any\]\]\] \| dict\[str, [Scanner](../reference/scanner.html.md#scanner)\[Any\]\] \| [ScanJob](../reference/scanning.html.md#scanjob) \| [ScanJobConfig](../reference/scanning.html.md#scanjobconfig)  
Scanners to execute (list, dict with explicit names, or ScanJob). If a [ScanJob](../reference/scanning.html.md#scanjob) or [ScanJobConfig](../reference/scanning.html.md#scanjobconfig) is specified, then its options are used as the default options for the scan.

`transcripts` [Transcripts](../reference/transcript.html.md#transcripts) \| None  
Transcripts to scan.

`scans` str \| None  
Location to write scan results (filesystem or S3 bucket). Defaults to “./scans”.

`worklist` Sequence\[[ScannerWork](../reference/scanning.html.md#scannerwork)\] \| Sequence\[[Worklist](../reference/scanning.html.md#worklist)\] \| str \| Path \| None  
Transcripts too process for each scanner (defaults to processing all transcripts). Either a list of [ScannerWork](../reference/scanning.html.md#scannerwork) or a YAML or JSON file with same.

`validation` str \| [ValidationSet](../reference/results.html.md#validationset) \| Mapping\[str, str \| [ValidationSet](../reference/results.html.md#validationset)\] \| None  
Validation cases to evaluate for scanners. Can be a file path (CSV, JSON, JSONL, YAML), a ValidationSet, or a dict mapping scanner names to file paths or ValidationSets.

`model` str \| [Model](https://inspect.aisi.org.uk/reference/inspect_ai.model.html#model) \| None  
Model to use for scanning by default (individual scanners can always call [get_model()](https://inspect.aisi.org.uk/reference/inspect_ai.model.html#get_model) to us arbitrary models). If not specified use the model specified in the scout project config (if any).

`model_config` [GenerateConfig](https://inspect.aisi.org.uk/reference/inspect_ai.model.html#generateconfig) \| None  
`GenerationConfig` for calls to the model.

`model_base_url` str \| None  
Base URL for communicating with the model API.

`model_args` dict\[str, Any\] \| str \| None  
Model creation args (as a dictionary or as a path to a JSON or YAML config file).

`model_roles` dict\[str, str \| [Model](https://inspect.aisi.org.uk/reference/inspect_ai.model.html#model)\] \| None  
Named roles for use in [get_model()](https://inspect.aisi.org.uk/reference/inspect_ai.model.html#get_model).

`max_transcripts` int \| None  
The maximum number of transcripts to process concurrently (this also serves as the default value for `max_connections`). Defaults to 25.

`max_processes` int \| None  
The maximum number of concurrent processes (for multiproccesing). Defaults to 4.

`limit` int \| None  
Limit the number of transcripts processed.

`shuffle` bool \| int \| None  
Shuffle the order of transcripts (pass an `int` to set a seed for shuffling).

`tags` list\[str\] \| None  
One or more tags for this scan.

`metadata` dict\[str, Any\] \| None  
Metadata for this scan.

`display` [DisplayType](https://inspect.aisi.org.uk/reference/inspect_ai.util.html#displaytype) \| None  
Display type: “rich”, “plain”, “log”, or “none” (defaults to “rich”).

`log_level` str \| None  
Level for logging to the console: “debug”, “http”, “sandbox”, “info”, “warning”, “error”, “critical”, or “notset” (defaults to “warning”)

`fail_on_error` bool  
Re-raise exceptions instead of capturing them in results. Defaults to False.

`dry_run` bool  
Don’t actually run the scan, just print the spec and return the status. Defaults to False.

`results` str \| None  

### scan_resume

Resume a previous scan.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/5282cf41f9ae85a8bc81a91585c6c3424508c536/src/inspect_scout/_scan.py#L343)

``` python
def scan_resume(
    scan_location: str,
    display: DisplayType | None = None,
    log_level: str | None = None,
    fail_on_error: bool = False,
) -> Status
```

`scan_location` str  
Scan location to resume from.

`display` [DisplayType](https://inspect.aisi.org.uk/reference/inspect_ai.util.html#displaytype) \| None  
Display type: “rich”, “plain”, “log”, or “none” (defaults to “rich”).

`log_level` str \| None  
Level for logging to the console: “debug”, “http”, “sandbox”, “info”, “warning”, “error”, “critical”, or “notset” (defaults to “warning”)

`fail_on_error` bool  
Re-raise exceptions instead of capturing them in results.

### scan_complete

Complete a scan.

This function is used to indicate that a scan with errors in some transcripts should be completed in spite of the errors.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/5282cf41f9ae85a8bc81a91585c6c3424508c536/src/inspect_scout/_scan.py#L413)

``` python
def scan_complete(
    scan_location: str,
    display: DisplayType | None = None,
    log_level: str | None = None,
) -> Status
```

`scan_location` str  
Scan location to complete.

`display` [DisplayType](https://inspect.aisi.org.uk/reference/inspect_ai.util.html#displaytype) \| None  
Display type: “rich”, “plain”, “log”, or “none” (defaults to “rich”).

`log_level` str \| None  
Level for logging to the console: “debug”, “http”, “sandbox”, “info”, “warning”, “error”, “critical”, or “notset” (defaults to “warning”)

## Jobs

### scanjob

Decorator for registering scan jobs.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/5282cf41f9ae85a8bc81a91585c6c3424508c536/src/inspect_scout/_scanjob.py#L299)

``` python
def scanjob(
    func: ScanJobType | None = None, *, name: str | None = None
) -> ScanJobType | Callable[[ScanJobType], ScanJobType]
```

`func` ScanJobType \| None  
Function returning [ScanJob](../reference/scanning.html.md#scanjob).

`name` str \| None  
Optional name for scanjob (defaults to function name).

### ScanJob

Scan job definition.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/5282cf41f9ae85a8bc81a91585c6c3424508c536/src/inspect_scout/_scanjob.py#L57)

``` python
class ScanJob
```

#### Attributes

`name` str \| None  
Name of scan job (defaults to @scanjob function name).

`transcripts` [Transcripts](../reference/transcript.html.md#transcripts) \| None  
Trasnscripts to scan.

`worklist` Sequence\[[Worklist](../reference/scanning.html.md#worklist)\] \| None  
Transcript ids to process for each scanner (defaults to processing all transcripts).

`validation` dict\[str, [ValidationSet](../reference/results.html.md#validationset)\] \| None  
Validation cases to apply.

`scanners` dict\[str, [Scanner](../reference/scanner.html.md#scanner)\[Any\]\]  
Scanners to apply to transcripts.

`scans` str \| None  
Location to write scan results (filesystem or S3 bucket). Defaults to “./scans”.

`model` [Model](https://inspect.aisi.org.uk/reference/inspect_ai.model.html#model) \| None  
Model to use for scanning by default (individual scanners can always call [get_model()](https://inspect.aisi.org.uk/reference/inspect_ai.model.html#get_model) to us arbitrary models).

If not specified use the value of the SCOUT_SCAN_MODEL environment variable.

`model_base_url` str \| None  
Base URL for communicating with the model API.

`model_args` dict\[str, Any\] \| None  
Model creation args (as a dictionary or as a path to a JSON or YAML config file).

`generate_config` [GenerateConfig](https://inspect.aisi.org.uk/reference/inspect_ai.model.html#generateconfig) \| None  
`GenerationConfig` for calls to the model.

`model_roles` dict\[str, [Model](https://inspect.aisi.org.uk/reference/inspect_ai.model.html#model)\] \| None  
Named roles for use in [get_model()](https://inspect.aisi.org.uk/reference/inspect_ai.model.html#get_model).

`max_transcripts` int \| None  
The maximum number of transcripts to process concurrently (this also serves as the default value for `max_connections`). Defaults to 25.

`max_processes` int \| None  
The maximum number of concurrent processes (for multiproccesing). Defaults to 4.

`limit` int \| None  
Limit the number of transcripts processed.

`shuffle` bool \| int \| None  
Shuffle the order of transcripts (pass an `int` to set a seed for shuffling).

`tags` list\[str\] \| None  
One or more tags for this scan.

`metadata` dict\[str, Any\] \| None  
Metadata for this scan.

`log_level` str \| None  
Level for logging to the console: “debug”, “http”, “sandbox”, “info”, “warning”, “error”, “critical”, or “notset” (defaults to “warning”).

### ScanJobConfig

Scan job configuration.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/5282cf41f9ae85a8bc81a91585c6c3424508c536/src/inspect_scout/_scanjob_config.py#L11)

``` python
class ScanJobConfig(BaseModel)
```

#### Attributes

`name` str \| None  
Name of scan job.

`transcripts` str \| None  
Trasnscripts to scan.

`filter` str \| list\[str\]  
SQL WHERE clause(s) for filtering transcripts.

`scanners` list\[[ScannerSpec](../reference/scanning.html.md#scannerspec)\] \| dict\[str, [ScannerSpec](../reference/scanning.html.md#scannerspec)\] \| None  
Scanners to apply to transcripts.

`worklist` list\[[Worklist](../reference/scanning.html.md#worklist)\] \| None  
Transcript ids to process for each scanner (defaults to processing all transcripts).

`validation` dict\[str, str \| [ValidationSet](../reference/results.html.md#validationset)\] \| None  
Validation cases to apply for scanners.

`scans` str \| None  
Location to write scan results (filesystem or S3 bucket). Defaults to “./scans”.

`model` str \| None  
Model to use for scanning by default (individual scanners can always call [get_model()](https://inspect.aisi.org.uk/reference/inspect_ai.model.html#get_model) to us arbitrary models).

If not specified use the value of the SCOUT_SCAN_MODEL environment variable.

`model_base_url` str \| None  
Base URL for communicating with the model API.

If not specified use the value of the SCOUT_SCAN_MODEL_BASE_URL environment variable.

`model_args` dict\[str, Any\] \| str \| None  
Model creation args (as a dictionary or as a path to a JSON or YAML config file).

If not specified use the value of the SCOUT_SCAN_MODEL_ARGS environment variable.

`generate_config` [GenerateConfig](https://inspect.aisi.org.uk/reference/inspect_ai.model.html#generateconfig) \| None  
`GenerationConfig` for calls to the model.

`model_roles` dict\[str, [ModelConfig](https://inspect.aisi.org.uk/reference/inspect_ai.model.html#modelconfig) \| str\] \| None  
Named roles for use in [get_model()](https://inspect.aisi.org.uk/reference/inspect_ai.model.html#get_model).

`max_transcripts` int \| None  
The maximum number of transcripts to process concurrently (this also serves as the default value for `max_connections`). Defaults to 25.

`max_processes` int \| None  
The maximum number of concurrent processes (for multiproccesing). Defaults to 4.

`limit` int \| None  
Limit the number of transcripts processed.

`shuffle` bool \| int \| None  
Shuffle the order of transcripts (pass an `int` to set a seed for shuffling).

`tags` list\[str\] \| None  
One or more tags for this scan.

`metadata` dict\[str, Any\] \| None  
Metadata for this scan.

`log_level` Literal\['debug', 'http', 'sandbox', 'info', 'warning', 'error', 'critical', 'notset'\] \| None  
Level for logging to the console: “debug”, “http”, “sandbox”, “info”, “warning”, “error”, “critical”, or “notset” (defaults to “warning”).

### ProjectConfig

Scout project configuration from scout.yaml.

Extends ScanJobConfig to represent project-level defaults. All fields from ScanJobConfig are available as project defaults.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/5282cf41f9ae85a8bc81a91585c6c3424508c536/src/inspect_scout/_project/types.py#L8)

``` python
class ProjectConfig(ScanJobConfig)
```

#### Attributes

`name` str \| None  
Name of scan job.

`transcripts` str \| None  
Trasnscripts to scan.

`filter` str \| list\[str\]  
SQL WHERE clause(s) for filtering transcripts.

`scanners` list\[[ScannerSpec](../reference/scanning.html.md#scannerspec)\] \| dict\[str, [ScannerSpec](../reference/scanning.html.md#scannerspec)\] \| None  
Scanners to apply to transcripts.

`worklist` list\[[Worklist](../reference/scanning.html.md#worklist)\] \| None  
Transcript ids to process for each scanner (defaults to processing all transcripts).

`validation` dict\[str, str \| [ValidationSet](../reference/results.html.md#validationset)\] \| None  
Validation cases to apply for scanners.

`scans` str \| None  
Location to write scan results (filesystem or S3 bucket). Defaults to “./scans”.

`model` str \| None  
Model to use for scanning by default (individual scanners can always call [get_model()](https://inspect.aisi.org.uk/reference/inspect_ai.model.html#get_model) to us arbitrary models).

If not specified use the value of the SCOUT_SCAN_MODEL environment variable.

`model_base_url` str \| None  
Base URL for communicating with the model API.

If not specified use the value of the SCOUT_SCAN_MODEL_BASE_URL environment variable.

`model_args` dict\[str, Any\] \| str \| None  
Model creation args (as a dictionary or as a path to a JSON or YAML config file).

If not specified use the value of the SCOUT_SCAN_MODEL_ARGS environment variable.

`generate_config` [GenerateConfig](https://inspect.aisi.org.uk/reference/inspect_ai.model.html#generateconfig) \| None  
`GenerationConfig` for calls to the model.

`model_roles` dict\[str, [ModelConfig](https://inspect.aisi.org.uk/reference/inspect_ai.model.html#modelconfig) \| str\] \| None  
Named roles for use in [get_model()](https://inspect.aisi.org.uk/reference/inspect_ai.model.html#get_model).

`max_transcripts` int \| None  
The maximum number of transcripts to process concurrently (this also serves as the default value for `max_connections`). Defaults to 25.

`max_processes` int \| None  
The maximum number of concurrent processes (for multiproccesing). Defaults to 4.

`limit` int \| None  
Limit the number of transcripts processed.

`shuffle` bool \| int \| None  
Shuffle the order of transcripts (pass an `int` to set a seed for shuffling).

`tags` list\[str\] \| None  
One or more tags for this scan.

`metadata` dict\[str, Any\] \| None  
Metadata for this scan.

`log_level` Literal\['debug', 'http', 'sandbox', 'info', 'warning', 'error', 'critical', 'notset'\] \| None  
Level for logging to the console: “debug”, “http”, “sandbox”, “info”, “warning”, “error”, “critical”, or “notset” (defaults to “warning”).

### ScannerSpec

Scanner used by scan.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/5282cf41f9ae85a8bc81a91585c6c3424508c536/src/inspect_scout/_scanspec.py#L22)

``` python
class ScannerSpec(BaseModel)
```

#### Attributes

`name` str  
Scanner name.

`version` int  
Scanner version.

`package_version` str \| None  
Scanner package version (if in a package).

`file` str \| None  
Scanner source file (if not in a package).

`params` dict\[str, Any\]  
Scanner arguments.

### ScannerWork

Definition of work to perform for a scanner.

By default scanners process all transcripts passed to [scan()](../reference/scanning.html.md#scan). You can alternately pass a list of [ScannerWork](../reference/scanning.html.md#scannerwork) to specify that only particular scanners and transcripts should be processed.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/5282cf41f9ae85a8bc81a91585c6c3424508c536/src/inspect_scout/_transcript/transcripts.py#L227)

``` python
class ScannerWork
```

#### Attributes

`scanner` str  
Scanner name.

`transcripts` list\[str\] \| [Transcripts](../reference/transcript.html.md#transcripts)  
Transcripts.

### Worklist

List of transcript ids to process for a scanner.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/5282cf41f9ae85a8bc81a91585c6c3424508c536/src/inspect_scout/_scanspec.py#L139)

``` python
class Worklist(BaseModel)
```

#### Attributes

`scanner` str  
Scanner name.

`transcripts` list\[str\]  
List of transcript ids.

## Configuration

### ScanSpec

Scan specification (scanners, transcripts, config).

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/5282cf41f9ae85a8bc81a91585c6c3424508c536/src/inspect_scout/_scanspec.py#L149)

``` python
class ScanSpec(BaseModel)
```

#### Attributes

`scan_id` str  
Globally unique id for scan job.

`scan_name` str  
Scan job name.

`scan_file` str \| None  
Source file for scan job.

`scan_args` dict\[str, Any\] \| None  
Arguments used for invoking the scan job.

`timestamp` datetime  
Time created.

`tags` list\[str\] \| None  
Tags associated with the scan.

`metadata` dict\[str, Any\] \| None  
Additional scan metadata.

`model` [ModelConfig](https://inspect.aisi.org.uk/reference/inspect_ai.model.html#modelconfig) \| None  
Model used for eval.

`model_roles` dict\[str, [ModelConfig](https://inspect.aisi.org.uk/reference/inspect_ai.model.html#modelconfig)\] \| None  
Model roles.

`revision` [ScanRevision](../reference/scanning.html.md#scanrevision) \| None  
Source revision of scan.

`packages` dict\[str, str\]  
Package versions for scan.

`options` [ScanOptions](../reference/scanning.html.md#scanoptions)  
Scan options.

`transcripts` [ScanTranscripts](../reference/scanning.html.md#scantranscripts) \| None  
Transcripts to scan.

`scanners` dict\[str, [ScannerSpec](../reference/scanning.html.md#scannerspec)\]  
Scanners to apply to transcripts.

`worklist` list\[[Worklist](../reference/scanning.html.md#worklist)\] \| None  
Transcript ids to process for each scanner (defaults to processing all transcripts).

`validation` dict\[str, [ValidationSet](../reference/results.html.md#validationset)\] \| None  
Validation cases to apply for scanners.

### ScanOptions

Options used for scan.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/5282cf41f9ae85a8bc81a91585c6c3424508c536/src/inspect_scout/_scanspec.py#L60)

``` python
class ScanOptions(BaseModel)
```

#### Attributes

`max_transcripts` int  
Maximum number of concurrent transcripts (defaults to 25).

`max_processes` int \| None  
Number of worker processes. Defaults to 4.

`limit` int \| None  
Transcript limit (maximum number of transcripts to read).

`shuffle` bool \| int \| None  
Shuffle order of transcripts.

### ScanRevision

Git revision for scan.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/5282cf41f9ae85a8bc81a91585c6c3424508c536/src/inspect_scout/_scanspec.py#L44)

``` python
class ScanRevision(BaseModel)
```

#### Attributes

`type` Literal\['git'\]  
Type of revision (currently only “git”)

`origin` str  
Revision origin server

`version` str  
Revision version (based on tags).

`commit` str  
Revision commit.

### ScanTranscripts

Transcripts targeted by a scan.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/5282cf41f9ae85a8bc81a91585c6c3424508c536/src/inspect_scout/_scanspec.py#L89)

``` python
class ScanTranscripts(BaseModel)
```

#### Attributes

`type` Literal\['eval_log', 'database'\]  
Transcripts backing store type (‘eval_log’ or ‘database’).

`location` str \| None  
Location of transcript collection (e.g. database location).

`filter` list\[str\] \| None  
Filter (SQL WHERE clauses) applied to transcripts for scan.

Note that `transcript_ids` already reflects the filter so it need not be re-applied.

`transcript_ids` dict\[str, str \| None\]  
IDs of transcripts mapped to optional location hints.

The location value depends on the backing store: - For parquet databases: the parquet filename containing the transcript - For eval logs: the log file path containing the transcript - For other stores (e.g., relational DB): may be None if ID alone suffices

### TranscriptField

Field in transcript data frame.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/5282cf41f9ae85a8bc81a91585c6c3424508c536/src/inspect_scout/_scanspec.py#L76)

``` python
class TranscriptField(TypedDict, total=False)
```
