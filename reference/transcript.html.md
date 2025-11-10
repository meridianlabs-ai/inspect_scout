# Transcript API


### transcripts_from_logs

Read sample transcripts from eval logs.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/73b9a4a0b804f2f44d0c06c51a7d611a96320dca/src/inspect_scout/_transcript/database.py#L363)

``` python
def transcripts_from_logs(logs: LogPaths) -> Transcripts
```

`logs` LogPaths  
Log paths as file(s) or directories.

### Transcripts

Collection of transcripts for scanning.

Transcript collections can be filtered using the `where()`, `limit()`,
and ’shuffle()\` methods. The transcripts are not modified in place so
the filtered transcripts should be referenced via the return value. For
example:

``` python
from inspect_scout import transcripts, log_metadata as m

transcripts = transcripts_from_logs("./logs")
transcripts = transcripts.where(m.task_name == "cybench")
```

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/73b9a4a0b804f2f44d0c06c51a7d611a96320dca/src/inspect_scout/_transcript/transcripts.py#L15)

``` python
class Transcripts(abc.ABC)
```

#### Methods

where  
Filter the transcript collection by a `Condition`.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/73b9a4a0b804f2f44d0c06c51a7d611a96320dca/src/inspect_scout/_transcript/transcripts.py#L37)

``` python
def where(self, condition: Condition) -> "Transcripts"
```

`condition` [Condition](transcript.qmd#condition)  
Filter condition.

for_validation  
Filter transcripts to only those with IDs matching validation cases.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/73b9a4a0b804f2f44d0c06c51a7d611a96320dca/src/inspect_scout/_transcript/transcripts.py#L50)

``` python
def for_validation(
    self, validation: ValidationSet | dict[str, ValidationSet]
) -> "Transcripts"
```

`validation` [ValidationSet](results.qmd#validationset) \| dict\[str, [ValidationSet](results.qmd#validationset)\]  
Validation object containing cases with target IDs.

limit  
Limit the number of transcripts processed.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/73b9a4a0b804f2f44d0c06c51a7d611a96320dca/src/inspect_scout/_transcript/transcripts.py#L113)

``` python
def limit(self, n: int) -> "Transcripts"
```

`n` int  
Limit on transcripts.

shuffle  
Shuffle the order of transcripts.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/73b9a4a0b804f2f44d0c06c51a7d611a96320dca/src/inspect_scout/_transcript/transcripts.py#L126)

``` python
def shuffle(self, seed: int | None = None) -> "Transcripts"
```

`seed` int \| None  
Random seed for shuffling.

count  
Number of transcripts in collection.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/73b9a4a0b804f2f44d0c06c51a7d611a96320dca/src/inspect_scout/_transcript/transcripts.py#L152)

``` python
@abc.abstractmethod
async def count(self) -> int
```

index  
Index of `TranscriptInfo` for the collection.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/73b9a4a0b804f2f44d0c06c51a7d611a96320dca/src/inspect_scout/_transcript/transcripts.py#L157)

``` python
@abc.abstractmethod
async def index(self) -> Iterator[TranscriptInfo]
```

### TranscriptInfo

Transcript identifier, location, and metadata.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/73b9a4a0b804f2f44d0c06c51a7d611a96320dca/src/inspect_scout/_transcript/types.py#L36)

``` python
class TranscriptInfo(BaseModel)
```

#### Attributes

`id` str  
Globally unique id for transcript (e.g. sample uuid).

`source_id` str  
Globally unique ID for transcript source (e.g. eval_id).

`source_uri` str  
URI for source data (e.g. log file path)

`score` JsonValue \| None  
Main score assigned to transcript (optional)

`scores` dict\[str, JsonValue\]  
All scores assigned to transcript.

`variables` dict\[str, JsonValue\]  
Variables (e.g. to be used in a prompt template) associated with
transcript (e.g. sample metadata).

`metadata` dict\[str, JsonValue\]  
Transcript source specific metadata (e.g. model, task name, errors,
epoch, dataset sample id, limits, etc.).

### Transcript

Transcript info and transcript content (messages and events).

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/73b9a4a0b804f2f44d0c06c51a7d611a96320dca/src/inspect_scout/_transcript/types.py#L61)

``` python
class Transcript(TranscriptInfo)
```

#### Attributes

`messages` list\[ChatMessage\]  
Main message thread.

`events` list\[Event\]  
Events from transcript.

### Column

Database column with comparison operators.

Supports various predicate functions including `like()`, `not_like()`,
`between()`, etc. Additionally supports standard python equality and
comparison operators (e.g. `==`, ’\>\`, etc.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/73b9a4a0b804f2f44d0c06c51a7d611a96320dca/src/inspect_scout/_transcript/metadata.py#L521)

``` python
class Column
```

#### Methods

in\_  
Check if value is in a list.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/73b9a4a0b804f2f44d0c06c51a7d611a96320dca/src/inspect_scout/_transcript/metadata.py#L563)

``` python
def in_(self, values: list[Any]) -> Condition
```

`values` list\[Any\]  

not_in  
Check if value is not in a list.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/73b9a4a0b804f2f44d0c06c51a7d611a96320dca/src/inspect_scout/_transcript/metadata.py#L567)

``` python
def not_in(self, values: list[Any]) -> Condition
```

`values` list\[Any\]  

like  
SQL LIKE pattern matching (case-sensitive).

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/73b9a4a0b804f2f44d0c06c51a7d611a96320dca/src/inspect_scout/_transcript/metadata.py#L571)

``` python
def like(self, pattern: str) -> Condition
```

`pattern` str  

not_like  
SQL NOT LIKE pattern matching (case-sensitive).

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/73b9a4a0b804f2f44d0c06c51a7d611a96320dca/src/inspect_scout/_transcript/metadata.py#L575)

``` python
def not_like(self, pattern: str) -> Condition
```

`pattern` str  

ilike  
PostgreSQL ILIKE pattern matching (case-insensitive).

Note: For SQLite and DuckDB, this will use LIKE with LOWER() for
case-insensitivity.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/73b9a4a0b804f2f44d0c06c51a7d611a96320dca/src/inspect_scout/_transcript/metadata.py#L579)

``` python
def ilike(self, pattern: str) -> Condition
```

`pattern` str  

not_ilike  
PostgreSQL NOT ILIKE pattern matching (case-insensitive).

Note: For SQLite and DuckDB, this will use NOT LIKE with LOWER() for
case-insensitivity.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/73b9a4a0b804f2f44d0c06c51a7d611a96320dca/src/inspect_scout/_transcript/metadata.py#L586)

``` python
def not_ilike(self, pattern: str) -> Condition
```

`pattern` str  

is_null  
Check if value is NULL.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/73b9a4a0b804f2f44d0c06c51a7d611a96320dca/src/inspect_scout/_transcript/metadata.py#L593)

``` python
def is_null(self) -> Condition
```

is_not_null  
Check if value is not NULL.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/73b9a4a0b804f2f44d0c06c51a7d611a96320dca/src/inspect_scout/_transcript/metadata.py#L597)

``` python
def is_not_null(self) -> Condition
```

between  
Check if value is between two values.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/73b9a4a0b804f2f44d0c06c51a7d611a96320dca/src/inspect_scout/_transcript/metadata.py#L601)

``` python
def between(self, low: Any, high: Any) -> Condition
```

`low` Any  
Lower bound (inclusive). If None, raises ValueError.

`high` Any  
Upper bound (inclusive). If None, raises ValueError.

not_between  
Check if value is not between two values.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/73b9a4a0b804f2f44d0c06c51a7d611a96320dca/src/inspect_scout/_transcript/metadata.py#L615)

``` python
def not_between(self, low: Any, high: Any) -> Condition
```

`low` Any  
Lower bound (inclusive). If None, raises ValueError.

`high` Any  
Upper bound (inclusive). If None, raises ValueError.

### Condition

WHERE clause condition that can be combined with others.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/73b9a4a0b804f2f44d0c06c51a7d611a96320dca/src/inspect_scout/_transcript/metadata.py#L64)

``` python
class Condition
```

#### Methods

to_sql  
Generate SQL WHERE clause and parameters.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/73b9a4a0b804f2f44d0c06c51a7d611a96320dca/src/inspect_scout/_transcript/metadata.py#L116)

``` python
def to_sql(
    self,
    dialect: Union[
        SQLDialect, Literal["sqlite", "duckdb", "postgres"]
    ] = SQLDialect.SQLITE,
) -> tuple[str, list[Any]]
```

`dialect` Union\[SQLDialect, Literal\['sqlite', 'duckdb', 'postgres'\]\]  
Target SQL dialect (sqlite, duckdb, or postgres).

### Metadata

Entry point for building metadata filter expressions.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/73b9a4a0b804f2f44d0c06c51a7d611a96320dca/src/inspect_scout/_transcript/metadata.py#L630)

``` python
class Metadata
```

### metadata

Metadata selector for where expressions.

Typically aliased to a more compact expression (e.g. `m`) for use in
queries). For example:

``` python
from inspect_scout import metadata as m
filter = m.model == "gpt-4"
filter = (m.task_name == "math") & (m.epochs > 1)
```

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/73b9a4a0b804f2f44d0c06c51a7d611a96320dca/src/inspect_scout/_transcript/metadata.py#L652)

``` python
metadata = Metadata()
```

### LogMetadata

Typed metadata interface for Inspect log transcripts.

Provides typed properties for standard Inspect log columns while
preserving the ability to access custom fields through the base Metadata
class methods.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/73b9a4a0b804f2f44d0c06c51a7d611a96320dca/src/inspect_scout/_transcript/log.py#L10)

``` python
class LogMetadata(Metadata)
```

#### Attributes

`sample_id` [Column](transcript.qmd#column)  
Unique id for sample.

`eval_id` [Column](transcript.qmd#column)  
Globally unique id for eval.

`log` [Column](transcript.qmd#column)  
Location that the log file was read from.

`eval_created` [Column](transcript.qmd#column)  
Time eval was created.

`eval_tags` [Column](transcript.qmd#column)  
Tags associated with evaluation run.

`eval_metadata` [Column](transcript.qmd#column)  
Additional eval metadata.

`task_name` [Column](transcript.qmd#column)  
Task name.

`task_args` [Column](transcript.qmd#column)  
Task arguments.

`solver` [Column](transcript.qmd#column)  
Solver name.

`solver_args` [Column](transcript.qmd#column)  
Arguments used for invoking the solver.

`model` [Column](transcript.qmd#column)  
Model used for eval.

`generate_config` [Column](transcript.qmd#column)  
Generate config specified for model instance.

`model_roles` [Column](transcript.qmd#column)  
Model roles.

`id` [Column](transcript.qmd#column)  
Unique id for sample.

`epoch` [Column](transcript.qmd#column)  
Epoch number for sample.

`input` [Column](transcript.qmd#column)  
Sample input.

`target` [Column](transcript.qmd#column)  
Sample target.

`sample_metadata` [Column](transcript.qmd#column)  
Sample metadata.

`score` [Column](transcript.qmd#column)  
Headline score value.

`total_tokens` [Column](transcript.qmd#column)  
Total tokens used for sample.

`total_time` [Column](transcript.qmd#column)  
Total time that the sample was running.

`working_time` [Column](transcript.qmd#column)  
Time spent working (model generation, sandbox calls, etc.).

`error` [Column](transcript.qmd#column)  
Error that halted the sample.

`limit` [Column](transcript.qmd#column)  
Limit that halted the sample.

### log_metadata

Log metadata selector for where expressions.

Typically aliased to a more compact expression (e.g. `m`) for use in
queries). For example:

``` python
from inspect_scout import log_metadata as m

# typed access to standard fields
filter = m.model == "gpt-4"
filter = (m.task_name == "math") & (m.epochs > 1)

# dynamic access to custom fields
filter = m["custom_field"] > 100
```

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/73b9a4a0b804f2f44d0c06c51a7d611a96320dca/src/inspect_scout/_transcript/log.py#L159)

``` python
log_metadata = LogMetadata()
```
