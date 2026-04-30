# Results – Inspect Scout

## Results

### scan_list

List completed and pending scans.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/85620b998ee7e398069aad6692134e2cc3662d8e/src/inspect_scout/_scanlist.py#L7)

``` python
def scan_list(scans_location: str) -> list[Status]
```

`scans_location` str  
Location of scans to list.

### scan_status

Status of scan.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/85620b998ee7e398069aad6692134e2cc3662d8e/src/inspect_scout/_scanresults.py#L20)

``` python
def scan_status(scan_location: str) -> Status
```

`scan_location` str  
Location to get status for (e.g. directory or s3 bucket)

### Status

Status of scan job.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/85620b998ee7e398069aad6692134e2cc3662d8e/src/inspect_scout/_recorder/recorder.py#L19)

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

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/85620b998ee7e398069aad6692134e2cc3662d8e/src/inspect_scout/_recorder/summary.py#L68)

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

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/85620b998ee7e398069aad6692134e2cc3662d8e/src/inspect_scout/_scanresults.py#L72)

``` python
def scan_results_df(
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
Row granularity. Specify “results” to yield a row for each scanner result (potentially multiple per transcript); Specify “transcript” to yield a row for each transcript (in which case multiple results will be packed into the `value` field as a JSON list of [Result](../reference/scanner.html.md#result)).

`exclude_columns` list\[str\] \| None  
List of column names to exclude when reading parquet files. Useful for reducing memory usage by skipping large unused columns.

### ScanResultsDF

Scan results as pandas data frames.

The `scanners` mapping provides lazy access to DataFrames - each DataFrame is only materialized when its key is accessed. This allows efficient access to specific scanner results without loading all data upfront.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/85620b998ee7e398069aad6692134e2cc3662d8e/src/inspect_scout/_recorder/recorder.py#L86)

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

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/85620b998ee7e398069aad6692134e2cc3662d8e/src/inspect_scout/_scanresults.py#L45)

``` python
def scan_results_arrow(
    scan_location: str,
) -> ScanResultsArrow
```

`scan_location` str  
Location of scan (e.g. directory or s3 bucket).

### ScanResultsArrow

Scan results as Arrow.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/85620b998ee7e398069aad6692134e2cc3662d8e/src/inspect_scout/_recorder/recorder.py#L39)

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

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/85620b998ee7e398069aad6692134e2cc3662d8e/src/inspect_scout/_recorder/recorder.py#L58)

``` python
@abc.abstractmethod
def reader(
    self,
    scanner: str,
    streaming_batch_size: int = 1024,
    exclude_columns: list[str] | None = None,
) -> pa.RecordBatchReader
```

`scanner` str  

`streaming_batch_size` int  

`exclude_columns` list\[str\] \| None  

## Validation

### validation_set

Create a validation set by reading cases from a file or data frame.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/85620b998ee7e398069aad6692134e2cc3662d8e/src/inspect_scout/_validation/validation.py#L15)

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

### ValidationSet

Validation set for a scanner.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/85620b998ee7e398069aad6692134e2cc3662d8e/src/inspect_scout/_validation/types.py#L64)

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

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/85620b998ee7e398069aad6692134e2cc3662d8e/src/inspect_scout/_validation/types.py#L10)

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

#### Methods

coerce_labels_to_bool  
Coerce label values to boolean for backwards compatibility.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/85620b998ee7e398069aad6692134e2cc3662d8e/src/inspect_scout/_validation/types.py#L46)

``` python
@field_validator("labels", mode="before")
@classmethod
def coerce_labels_to_bool(cls, v: Any) -> dict[str, bool] | None
```

`v` Any  

### PredicateType

String name of a built-in validation predicate.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/85620b998ee7e398069aad6692134e2cc3662d8e/src/inspect_scout/_validation/predicates.py#L15)

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

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/85620b998ee7e398069aad6692134e2cc3662d8e/src/inspect_scout/_validation/predicates.py#L9)

``` python
PredicateFn: TypeAlias = Callable[
    [Result, JsonValue], Awaitable[bool | dict[str, bool]]
]
```

### ValidationPredicate

Predicate used to compare scanner result with target value.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/85620b998ee7e398069aad6692134e2cc3662d8e/src/inspect_scout/_validation/predicates.py#L31)

``` python
ValidationPredicate: TypeAlias = PredicateType | PredicateFn
```
