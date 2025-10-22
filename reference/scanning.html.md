# Scanning


## Scanning

### scan

Scan transcripts.

Scan transcripts using one or more scanners. Note that scanners must
each have a unique name. If you have more than one instance of a scanner
with the same name, numbered prefixes will be automatically assigned.
Alternatively, you can pass tuples of (name,scanner) or a dict with
explicit names for each scanner.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/b27eb2e6505608415b3a945a3e902c144bacd8be/src/inspect_scout/_scan.py#L56)

``` python
def scan(
    scanners: Sequence[Scanner[ScannerInput] | tuple[str, Scanner[ScannerInput]]]
    | dict[str, Scanner[ScannerInput]]
    | ScanJob,
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
    display: DisplayType | None = None,
    log_level: str | None = None,
) -> Status
```

`scanners` Sequence\[[Scanner](scanner.qmd#scanner)\[[ScannerInput](scanner.qmd#scannerinput)\] \| tuple\[str, [Scanner](scanner.qmd#scanner)\[[ScannerInput](scanner.qmd#scannerinput)\]\]\] \| dict\[str, [Scanner](scanner.qmd#scanner)\[[ScannerInput](scanner.qmd#scannerinput)\]\] \| [ScanJob](scanning.qmd#scanjob)  
Scanners to apply to transcripts.

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

`display` DisplayType \| None  
Display type: “rich”, “plain”, or “none” (defaults to “rich”).

`log_level` str \| None  
Level for logging to the console: “debug”, “http”, “sandbox”, “info”,
“warning”, “error”, “critical”, or “notset” (defaults to “warning”)

### scan_resume

Resume a previous scan.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/b27eb2e6505608415b3a945a3e902c144bacd8be/src/inspect_scout/_scan.py#L235)

``` python
def scan_resume(
    scan_location: str,
    display: DisplayType | None = None,
    log_level: str | None = None,
) -> Status
```

`scan_location` str  
Scan location to resume from.

`display` DisplayType \| None  
Display type: “rich”, “plain”, or “none” (defaults to “rich”).

`log_level` str \| None  
Level for logging to the console: “debug”, “http”, “sandbox”, “info”,
“warning”, “error”, “critical”, or “notset” (defaults to “warning”)

### scan_complete

Complete a scan.

This function is used to indicate that a scan with errors in some
transcripts should be completed in spite of the errors.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/b27eb2e6505608415b3a945a3e902c144bacd8be/src/inspect_scout/_scan.py#L295)

``` python
def scan_complete(
    scan_location: str,
    display: DisplayType | None = None,
    log_level: str | None = None,
) -> Status
```

`scan_location` str  
Scan location to complete.

`display` DisplayType \| None  
Display type: “rich”, “plain”, or “none” (defaults to “rich”).

`log_level` str \| None  
Level for logging to the console: “debug”, “http”, “sandbox”, “info”,
“warning”, “error”, “critical”, or “notset” (defaults to “warning”)

## Status

### Status

Status of scan job.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/b27eb2e6505608415b3a945a3e902c144bacd8be/src/inspect_scout/_recorder/recorder.py#L15)

``` python
@dataclass
class Status
```

#### Attributes

`complete` bool  
Is the job complete (all transcripts scanned).

`spec` ScanSpec  
Scan spec (transcripts, scanners, options).

`location` str  
Location of scan directory.

`summary` [Summary](results.qmd#summary)  
Summary of scan (results, errors, tokens, etc.)

`errors` list\[[Error](scanner.qmd#error)\]  
Errors during last scan attempt.

### ScanOptions

Options used for scan.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/b27eb2e6505608415b3a945a3e902c144bacd8be/src/inspect_scout/_scanspec.py#L44)

``` python
class ScanOptions(BaseModel)
```

#### Attributes

`max_transcripts` int  
Maximum number of concurrent transcripts (defaults to 25).

`max_processes` int  
Number of worker processes. Defaults to `multiprocessing.cpu_count()`.

`limit` int \| None  
Transcript limit (maximum number of transcripts to read).

`shuffle` bool \| int \| None  
Shuffle order of transcripts.

### ScanScanner

Scanner used by scan.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/b27eb2e6505608415b3a945a3e902c144bacd8be/src/inspect_scout/_scanspec.py#L18)

``` python
class ScanScanner(BaseModel)
```

#### Attributes

`name` str  
Scanner name.

`file` str \| None  
Scanner source file (if not in a package).

`params` dict\[str, Any\]  
Scanner arguments.

### ScanRevision

Git revision for scan.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/b27eb2e6505608415b3a945a3e902c144bacd8be/src/inspect_scout/_scanspec.py#L31)

``` python
class ScanRevision(BaseModel)
```

#### Attributes

`type` Literal\['git'\]  
Type of revision (currently only “git”)

`origin` str  
Revision origin server

`commit` str  
Revision commit.

### ScanTranscripts

Transcripts target by a scan.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/b27eb2e6505608415b3a945a3e902c144bacd8be/src/inspect_scout/_scanspec.py#L73)

``` python
class ScanTranscripts(BaseModel)
```

#### Attributes

`type` str  
Transcripts backing store type (currently only ‘eval_log’).

`fields` list\[[TranscriptField](scanning.qmd#transcriptfield)\]  
Data types of transcripts fields.

`count` int  
Trancript count.

`data` str  
Transcript data as a csv.

### TranscriptField

Field in transcript data frame.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/b27eb2e6505608415b3a945a3e902c144bacd8be/src/inspect_scout/_scanspec.py#L60)

``` python
class TranscriptField(TypedDict, total=False)
```

#### Attributes

`name` Required\[str\]  
Field name.

`type` Required\[str\]  
Field type (“integer”, “number”, “boolean”, “string”, or “datetime”)

`tz` NotRequired\[str\]  
Timezone (for “datetime” fields).

## Jobs

### scanjob

Decorator for registering scan jobs.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/b27eb2e6505608415b3a945a3e902c144bacd8be/src/inspect_scout/_scanjob.py#L107)

``` python
def scanjob(
    func: ScanJobType | None = None, *, name: str | None = None
) -> ScanJobType | Callable[[ScanJobType], ScanJobType]
```

`func` ScanJobType \| None  
Function returning `ScanJob`.

`name` str \| None  
Optional name for scanjob (defaults to function name).

### ScanJob

Scan job definition.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/b27eb2e6505608415b3a945a3e902c144bacd8be/src/inspect_scout/_scanjob.py#L28)

``` python
class ScanJob
```

#### Attributes

`name` str  
Name of scan job (defaults to @scanjob function name).

`transcripts` [Transcripts](transcript.qmd#transcripts) \| None  
Trasnscripts to scan.

`scanners` dict\[str, [Scanner](scanner.qmd#scanner)\[[ScannerInput](scanner.qmd#scannerinput)\]\]  
Scanners to apply to transcripts.
