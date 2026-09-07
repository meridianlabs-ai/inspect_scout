# Results – Inspect Scout

## Results

### scan_list

List completed and pending scans.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/bef39729ae3a66084571cac3523e942d3feae561/src/inspect_scout/_scanlist.py#L7)

``` python
def scan_list(scans_location: str) -> list[Status]
```

`scans_location` str  
Location of scans to list.

### scan_status

Status of scan.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/bef39729ae3a66084571cac3523e942d3feae561/src/inspect_scout/_scanresults.py#L23)

``` python
def scan_status(scan_location: str) -> Status
```

`scan_location` str  
Location to get status for (e.g. directory or s3 bucket)

### Status

Status of scan job.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/bef39729ae3a66084571cac3523e942d3feae561/src/inspect_scout/_recorder/recorder.py#L42)

``` python
@dataclass
class Status
```

#### Attributes

`complete` bool  
Is the job complete (all transcripts scanned).

`spec` [ScanSpec](../reference/scanning.html.md#scanspec)  
Scan spec (transcripts, scanners, options).

`location` str  
Location of scan directory.

`summary` [Summary](../reference/results.html.md#summary)  
Summary of scan (results, errors, tokens, etc.)

`errors` list\[[Error](../reference/scanner.html.md#error)\]  
Errors during last scan attempt.

### Summary

Summary of scan results.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/bef39729ae3a66084571cac3523e942d3feae561/src/inspect_scout/_recorder/summary.py#L68)

``` python
class Summary(BaseModel)
```

#### Attributes

`complete` bool  
Is the scan complete?

`scanners` dict\[str, ScannerSummary\]  
Summary for each scanner.

### scan_results_df

Scan results as Pandas data frames.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/bef39729ae3a66084571cac3523e942d3feae561/src/inspect_scout/_scanresults.py#L75)

``` python
def scan_results_df(
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

### ScanResultsDF

Scan results as pandas data frames.

The `scanners` mapping provides lazy access to DataFrames - each DataFrame is only materialized when its key is accessed. This allows efficient access to specific scanner results without loading all data upfront.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/bef39729ae3a66084571cac3523e942d3feae561/src/inspect_scout/_recorder/recorder.py#L132)

``` python
@dataclass
class ScanResultsDF(Status)
```

#### Attributes

`complete` bool  
Is the job complete (all transcripts scanned).

`spec` [ScanSpec](../reference/scanning.html.md#scanspec)  
Scan spec (transcripts, scanners, options).

`location` str  
Location of scan directory.

`summary` [Summary](../reference/results.html.md#summary)  
Summary of scan (results, errors, tokens, etc.)

`errors` list\[[Error](../reference/scanner.html.md#error)\]  
Errors during last scan attempt.

`scanners` Mapping\[str, pd.DataFrame\]  
Mapping of scanner name to pandas data frame (lazily loaded).

### scan_results_arrow

Scan results as Arrow.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/bef39729ae3a66084571cac3523e942d3feae561/src/inspect_scout/_scanresults.py#L48)

``` python
def scan_results_arrow(
    scan_location: str,
) -> ScanResultsArrow
```

`scan_location` str  
Location of scan (e.g. directory or s3 bucket).

### ScanResultsArrow

Scan results as Arrow.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/bef39729ae3a66084571cac3523e942d3feae561/src/inspect_scout/_recorder/recorder.py#L62)

``` python
@dataclass
class ScanResultsArrow(Status)
```

#### Attributes

`complete` bool  
Is the job complete (all transcripts scanned).

`spec` [ScanSpec](../reference/scanning.html.md#scanspec)  
Scan spec (transcripts, scanners, options).

`location` str  
Location of scan directory.

`summary` [Summary](../reference/results.html.md#summary)  
Summary of scan (results, errors, tokens, etc.)

`errors` list\[[Error](../reference/scanner.html.md#error)\]  
Errors during last scan attempt.

`scanners` list\[str\]  
Scanner names.

#### Methods

reader  
Acquire a reader for the specified scanner.

The return reader is a context manager that should be acquired before reading.

`exclude_columns=None` (the default) excludes the heavy columns (`input`, `input_data`, and `scan_events`, available as [HEAVY_COLUMNS](../reference/results.html.md#heavy_columns)); pass `[]` to include all columns, or an explicit sequence to exclude exactly those columns.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/bef39729ae3a66084571cac3523e942d3feae561/src/inspect_scout/_recorder/recorder.py#L81)

``` python
@abc.abstractmethod
def reader(
    self,
    scanner: str,
    streaming_batch_size: int = 1024,
    exclude_columns: Sequence[str] | None = None,
) -> pa.RecordBatchReader
```

`scanner` str  

`streaming_batch_size` int  

`exclude_columns` Sequence\[str\] \| None  

### scan_results_batches

Stream a scanner’s results as pandas DataFrame batches.

Concatenating all batches yields the same rows as `scan_results_df(scan_location, scanner=scanner, rows=rows)`, but memory remains bounded by `batch_size` rather than scaling with the size of the scanner’s results. This holds for local paths and for cloud locations PyArrow can read natively (`s3://`, `gs://`, `abfs://`), which are read with HTTP range requests. Remote protocols PyArrow has no native filesystem for (e.g. `az://`) are the exception: the parquet file is downloaded in full before batching, so memory scales with file size.

Note that batches are produced with synchronous parquet I/O. To consume from async code, drive the iterator from a worker thread or use [scan_results_batches_async()](../reference/aio.html.md#scan_results_batches_async).

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/bef39729ae3a66084571cac3523e942d3feae561/src/inspect_scout/_scanresults.py#L162)

``` python
def scan_results_batches(
    scan_location: str,
    scanner: str,
    *,
    batch_size: int = 1024,
    exclude_columns: Sequence[str] | None = None,
    rows: Literal["results", "transcripts"] = "results",
) -> Iterator[pd.DataFrame]
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

### HEAVY_COLUMNS

Large JSON columns excluded by default when reading scan results.

These columns (full serialized scanner input, deduplicated message/call pools, and scanner execution events) dominate parquet file size and memory usage, and the common case (analysis over values/scores/metadata) never needs them. Pass `exclude_columns=[]` to include all columns.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/bef39729ae3a66084571cac3523e942d3feae561/src/inspect_scout/_recorder/recorder.py#L22)

``` python
HEAVY_COLUMNS: tuple[str, ...] = ("input", "input_data", "scan_events")
```

## Validation

### validation_set

Create a validation set by reading cases from a file or data frame.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/bef39729ae3a66084571cac3523e942d3feae561/src/inspect_scout/_validation/validation.py#L15)

``` python
def validation_set(
    cases: str | Path | pd.DataFrame,
    predicate: ValidationPredicate | None = "eq",
    split: str | list[str] | None = None,
) -> ValidationSet
```

`cases` str \| Path \| pd.DataFrame  
Path to a CSV, YAML, JSON, or JSONL file with validation cases, or data frame with validation cases.

`predicate` [ValidationPredicate](../reference/results.html.md#validationpredicate) \| None  
Predicate for comparing scanner results to validation targets (defaults to equality comparison). For single-value targets, compares value to target directly. For dict targets, string/single-value predicates are applied to each key, while multi-value predicates receive the full dicts.

`split` str \| list\[str\] \| None  
Optional split name(s) to filter cases by. Only cases with matching split values will be included. Can be a single split name or a list of split names. Cases without a split field are excluded when filtering.

### validation_predicate

Register a portable custom validation predicate.

Registered predicates are persisted by name and Inspect registry-compatible creation parameters rather than by serializing their Python implementation.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/bef39729ae3a66084571cac3523e942d3feae561/src/inspect_scout/_validation/registry.py#L42)

``` python
def validation_predicate(
    factory: PredicateFactory[P] | None = None,
    *,
    name: str | None = None,
) -> (
    RegisteredPredicateFactory[P]
    | Callable[[PredicateFactory[P]], RegisteredPredicateFactory[P]]
)
```

`factory` PredicateFactory\[P\] \| None  
Function that creates an async validation predicate.

`name` str \| None  
Optional registered name (defaults to the factory name).

### ValidationSet

Validation set for a scanner.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/bef39729ae3a66084571cac3523e942d3feae561/src/inspect_scout/_validation/types.py#L76)

``` python
class ValidationSet(BaseModel)
```

#### Attributes

`cases` list\[[ValidationCase](../reference/results.html.md#validationcase)\]  
Cases to compare scanner values against.

`predicate` [ValidationPredicate](../reference/results.html.md#validationpredicate) \| None  
Predicate for comparing scanner results to validation targets.

For single-value targets, the predicate compares value to target directly. For dict targets, string/single-value predicates are applied to each key, while multi-value predicates receive the full dicts.

`split` str \| list\[str\] \| None  
Active split filter applied to this validation set (informational).

### ValidationCase

Validation case for comparing to scanner results.

A [ValidationCase](../reference/results.html.md#validationcase) specifies the ground truth for a scan of particular id (e.g. transcript id, message id, etc.

Use `target` for single-value or dict validation. Use `labels` for validating resultsets with label-specific expectations.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/bef39729ae3a66084571cac3523e942d3feae561/src/inspect_scout/_validation/types.py#L16)

``` python
class ValidationCase(BaseModel)
```

#### Attributes

`id` str \| list\[str\]  
Target id (e.g. transcript_id, message, id, etc.)

`target` JsonValue \| None  
Target value that the scanner is expected to output.

For single-value results, this is the expected value. For dict-valued results, this is a dict of expected values.

`labels` dict\[str, bool\] \| None  
Label presence/absence expectations for resultset validation.

Maps label names to boolean expectations: - true: expect at least one result with a positive (non-negative) value - false: expect no results, or all results have negative values

`predicate` [PredicateType](../reference/results.html.md#predicatetype) \| None  
Predicate for comparing scanner result to target (e.g., ‘eq’, ‘gte’, ‘contains’).

When set, this per-case predicate overrides the global predicate on ValidationSet.

`split` str \| None  
Optional split name for organizing cases (e.g., ‘dev’, ‘test’, ‘train’).

`task_id` str \| None  
Optional sample identifier from the source eval log (informational only).

`task_repeat` int \| None  
Optional epoch/repeat number from the source eval log (informational only).

#### Methods

coerce_labels_to_bool  
Coerce label values to boolean for backwards compatibility.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/bef39729ae3a66084571cac3523e942d3feae561/src/inspect_scout/_validation/types.py#L58)

``` python
@field_validator("labels", mode="before")
@classmethod
def coerce_labels_to_bool(cls, v: Any) -> dict[str, bool] | None
```

`v` Any  

### PredicateType

String name of a built-in validation predicate.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/bef39729ae3a66084571cac3523e942d3feae561/src/inspect_scout/_validation/predicates.py#L16)

``` python
PredicateType: TypeAlias = Literal[
    "gt",
    "gte",
    "lt",
    "lte",
    "eq",
    "ne",
    "contains",
    "startswith",
    "endswith",
    "icontains",
    "iequals",
]
```

### PredicateFn

Function that implements a validation predicate.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/bef39729ae3a66084571cac3523e942d3feae561/src/inspect_scout/_validation/predicates.py#L10)

``` python
PredicateFn: TypeAlias = Callable[
    [Result, JsonValue], Awaitable[bool | dict[str, bool]]
]
```

### ValidationPredicate

Predicate used to compare scanner result with target value.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/bef39729ae3a66084571cac3523e942d3feae561/src/inspect_scout/_validation/predicates.py#L32)

``` python
ValidationPredicate: TypeAlias = PredicateType | PredicateFn
```
