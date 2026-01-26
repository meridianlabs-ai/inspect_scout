# Transcript API


## Reading

### transcripts_from

Read transcripts for scanning.

Transcripts may be stored in a `TranscriptDB` or may be Inspect eval
logs.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/1022e1f00bb1257f0ee493e0e6a1610878b9586c/src/inspect_scout/_transcript/factory.py#L19)

``` python
def transcripts_from(location: str | Logs) -> Transcripts
```

`location` str \| Logs  
Transcripts location. Either a path to a transcript database or path(s)
to Inspect eval logs.

### Transcript

Transcript info and transcript content (messages and events).

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/1022e1f00bb1257f0ee493e0e6a1610878b9586c/src/inspect_scout/_transcript/types.py#L119)

``` python
class Transcript(TranscriptInfo)
```

#### Attributes

`transcript_id` str  
Globally unique id for transcript (e.g. sample uuid).

`source_type` str \| None  
Type of source for transcript (e.g. “eval_log”).

`source_id` str \| None  
Globally unique ID for transcript source (e.g. eval_id).

`source_uri` str \| None  
Optional. URI for source data (e.g. log file path).

`date` str \| None  
Date/time when the transcript was created.

`task_set` str \| None  
Set from which transcript task was drawn (e.g. benchmark name).

`task_id` str \| None  
Identifier for task (e.g. dataset sample id).

`task_repeat` int \| None  
Repeat for a given task id within a task set (e.g. epoch).

`agent` str \| None  
Agent used to to execute task..

`agent_args` dict\[str, Any\] \| None  
Arguments passed to create agent.

`model` str \| None  
Main model used by agent.

`model_options` dict\[str, Any\] \| None  
Generation options for main model.

`score` JsonValue \| None  
Value indicating score on task.

`success` bool \| None  
Boolean reduction of score to succeeded/failed.

`message_count` int \| None  
Total messages in conversation.

`total_time` float \| None  
Time required to execute task (seconds).

`total_tokens` int \| None  
Tokens spent in execution of task.

`error` str \| None  
“Error message that terminated the task.

`limit` str \| None  
Limit that caused the task to exit (e.g. “tokens”, “messages, etc.).

`metadata` dict\[str, Any\]  
Transcript source specific metadata.

`messages` list\[ChatMessage\]  
Main message thread.

`events` list\[Event\]  
Events from transcript.

### Transcripts

Collection of transcripts for scanning.

Transcript collections can be filtered using the `where()`, `limit()`,
`shuffle()`, and `order_by()` methods. The transcripts are not modified
in place so the filtered transcripts should be referenced via the return
value. For example:

``` python
from inspect_scout import transcripts, columns as c

transcripts = transcripts_from("./logs")
transcripts = transcripts.where(c.task_set == "cybench")
```

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/1022e1f00bb1257f0ee493e0e6a1610878b9586c/src/inspect_scout/_transcript/transcripts.py#L56)

``` python
class Transcripts(abc.ABC)
```

#### Methods

where  
Filter the transcript collection by a SQL WHERE clause or `Condition`.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/1022e1f00bb1257f0ee493e0e6a1610878b9586c/src/inspect_scout/_transcript/transcripts.py#L75)

``` python
def where(self, condition: str | Condition) -> "Transcripts"
```

`condition` str \| [Condition](transcript.qmd#condition)  
Filter condition.

for_validation  
Filter transcripts to only those with IDs matching validation cases.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/1022e1f00bb1257f0ee493e0e6a1610878b9586c/src/inspect_scout/_transcript/transcripts.py#L91)

``` python
def for_validation(
    self, validation: str | ValidationSet | Mapping[str, str | ValidationSet]
) -> "Transcripts"
```

`validation` str \| [ValidationSet](results.qmd#validationset) \| Mapping\[str, str \| [ValidationSet](results.qmd#validationset)\]  
Validation cases to filter by. Can be a file path (CSV, JSON, JSONL,
YAML), a ValidationSet, or a dict mapping scanner names to file paths or
ValidationSets.

limit  
Limit the number of transcripts processed.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/1022e1f00bb1257f0ee493e0e6a1610878b9586c/src/inspect_scout/_transcript/transcripts.py#L164)

``` python
def limit(self, n: int) -> "Transcripts"
```

`n` int  
Limit on transcripts.

shuffle  
Shuffle the order of transcripts.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/1022e1f00bb1257f0ee493e0e6a1610878b9586c/src/inspect_scout/_transcript/transcripts.py#L177)

``` python
def shuffle(self, seed: int | None = None) -> "Transcripts"
```

`seed` int \| None  
Random seed for shuffling.

order_by  
Order transcripts by column.

Can be chained multiple times for tie-breaking. If shuffle() is also
used, shuffle takes precedence.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/1022e1f00bb1257f0ee493e0e6a1610878b9586c/src/inspect_scout/_transcript/transcripts.py#L190)

``` python
def order_by(
    self, column: Column, direction: Literal["ASC", "DESC"] = "ASC"
) -> "Transcripts"
```

`column` [Column](transcript.qmd#column)  
Column to sort by.

`direction` Literal\['ASC', 'DESC'\]  
Sort direction (“ASC” or “DESC”).

reader  
Read the selected transcripts.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/1022e1f00bb1257f0ee493e0e6a1610878b9586c/src/inspect_scout/_transcript/transcripts.py#L209)

``` python
@abc.abstractmethod
def reader(self, snapshot: ScanTranscripts | None = None) -> TranscriptsReader
```

`snapshot` [ScanTranscripts](scanning.qmd#scantranscripts) \| None  
An optional snapshot which provides hints to make the reader more
efficient (e.g. by preventing a full scan to find transcript_id =\>
filename mappings)

from_snapshot  
Restore transcripts from a snapshot.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/1022e1f00bb1257f0ee493e0e6a1610878b9586c/src/inspect_scout/_transcript/transcripts.py#L220)

``` python
@staticmethod
@abc.abstractmethod
def from_snapshot(snapshot: ScanTranscripts) -> "Transcripts"
```

`snapshot` [ScanTranscripts](scanning.qmd#scantranscripts)  

### TranscriptsReader

Read transcripts based on a `TranscriptsQuery`.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/1022e1f00bb1257f0ee493e0e6a1610878b9586c/src/inspect_scout/_transcript/transcripts.py#L16)

``` python
class TranscriptsReader(abc.ABC)
```

#### Methods

index  
Index of `TranscriptInfo` for the collection.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/1022e1f00bb1257f0ee493e0e6a1610878b9586c/src/inspect_scout/_transcript/transcripts.py#L32)

``` python
@abc.abstractmethod
def index(self) -> AsyncIterator[TranscriptInfo]
```

read  
Read transcript content.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/1022e1f00bb1257f0ee493e0e6a1610878b9586c/src/inspect_scout/_transcript/transcripts.py#L37)

``` python
@abc.abstractmethod
async def read(
    self, transcript: TranscriptInfo, content: TranscriptContent
) -> Transcript
```

`transcript` TranscriptInfo  
Transcript to read.

`content` TranscriptContent  
Content to read (e.g. specific message types, etc.)

## Database

### transcripts_db

Read/write interface to transcripts database.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/1022e1f00bb1257f0ee493e0e6a1610878b9586c/src/inspect_scout/_transcript/database/factory.py#L36)

``` python
def transcripts_db(location: str) -> TranscriptsDB
```

`location` str  
Database location (e.g. directory or S3 bucket).

### transcripts_db_schema

Get transcript database schema in various formats.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/1022e1f00bb1257f0ee493e0e6a1610878b9586c/src/inspect_scout/_transcript/database/schema.py#L191)

``` python
def transcripts_db_schema(
    format: Literal["pyarrow", "avro", "json", "pandas"] = "pyarrow",
) -> pa.Schema | dict[str, Any] | pd.DataFrame
```

`format` Literal\['pyarrow', 'avro', 'json', 'pandas'\]  
Output format: - “pyarrow”: PyArrow Schema for creating Parquet files -
“avro”: Avro schema as dict (JSON-serializable) - “json”: JSON Schema as
dict - “pandas”: Empty DataFrame with correct dtypes

### TranscriptsDB

Database of transcripts with write capability.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/1022e1f00bb1257f0ee493e0e6a1610878b9586c/src/inspect_scout/_transcript/database/database.py#L115)

``` python
class TranscriptsDB(TranscriptsView)
```

#### Methods

connect  
Connect to transcripts database.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/1022e1f00bb1257f0ee493e0e6a1610878b9586c/src/inspect_scout/_transcript/database/database.py#L22)

``` python
@abc.abstractmethod
async def connect(self) -> None
```

disconnect  
Disconnect from transcripts database.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/1022e1f00bb1257f0ee493e0e6a1610878b9586c/src/inspect_scout/_transcript/database/database.py#L27)

``` python
@abc.abstractmethod
async def disconnect(self) -> None
```

transcript_ids  
Get transcript IDs matching query.

Optimized method that returns only transcript IDs without loading full
metadata.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/1022e1f00bb1257f0ee493e0e6a1610878b9586c/src/inspect_scout/_transcript/database/database.py#L47)

``` python
@abc.abstractmethod
async def transcript_ids(self, query: Query | None = None) -> dict[str, str | None]
```

`query` Query \| None  
Query with where/limit/shuffle/order_by criteria.

select  
Select transcripts matching query.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/1022e1f00bb1257f0ee493e0e6a1610878b9586c/src/inspect_scout/_transcript/database/database.py#L62)

``` python
@abc.abstractmethod
def select(self, query: Query | None = None) -> AsyncIterator[TranscriptInfo]
```

`query` Query \| None  
Query with where/limit/shuffle/order_by criteria.

count  
Count transcripts matching query.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/1022e1f00bb1257f0ee493e0e6a1610878b9586c/src/inspect_scout/_transcript/database/database.py#L71)

``` python
@abc.abstractmethod
async def count(self, query: Query | None = None) -> int
```

`query` Query \| None  
Query with where criteria (limit/shuffle/order_by ignored).

read  
Read transcript content.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/1022e1f00bb1257f0ee493e0e6a1610878b9586c/src/inspect_scout/_transcript/database/database.py#L83)

``` python
@abc.abstractmethod
async def read(
    self,
    t: TranscriptInfo,
    content: TranscriptContent,
    max_bytes: int | None = None,
) -> Transcript
```

`t` TranscriptInfo  
Transcript to read.

`content` TranscriptContent  
Content to read (messages, events, etc.)

`max_bytes` int \| None  
Max content size in bytes. Raises TranscriptTooLargeError if exceeded.

distinct  
Get distinct values of a column, sorted ascending.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/1022e1f00bb1257f0ee493e0e6a1610878b9586c/src/inspect_scout/_transcript/database/database.py#L99)

``` python
@abc.abstractmethod
async def distinct(
    self, column: str, condition: Condition | None
) -> list[ScalarValue]
```

`column` str  
Column to get distinct values for.

`condition` [Condition](transcript.qmd#condition) \| None  
Filter condition, or None for no filter.

insert  
Insert transcripts into database.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/1022e1f00bb1257f0ee493e0e6a1610878b9586c/src/inspect_scout/_transcript/database/database.py#L118)

``` python
@abc.abstractmethod
async def insert(
    self,
    transcripts: Iterable[Transcript]
    | AsyncIterable[Transcript]
    | Transcripts
    | pa.RecordBatchReader,
    commit: bool = True,
) -> None
```

`transcripts` Iterable\[[Transcript](transcript.qmd#transcript)\] \| AsyncIterable\[[Transcript](transcript.qmd#transcript)\] \| [Transcripts](transcript.qmd#transcripts) \| pa.RecordBatchReader  
Transcripts to insert (iterable, async iterable, or source).

`commit` bool  
If True (default), commit after insert (compact + index). If False,
defer commit for batch operations. Call commit() explicitly when ready
to finalize.

commit  
Commit pending changes.

For parquet: compacts data files + rebuilds index. For relational DBs:
may be a no-op or transaction commit.

This is called automatically when insert() is called with commit=True
(the default). Only call this manually when using commit=False with
insert() for batch operations.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/1022e1f00bb1257f0ee493e0e6a1610878b9586c/src/inspect_scout/_transcript/database/database.py#L137)

``` python
@abc.abstractmethod
async def commit(self) -> None
```

## Filtering

### Column

Database column with comparison operators.

Supports various predicate functions including `like()`, `not_like()`,
`between()`, etc. Additionally supports standard python equality and
comparison operators (e.g. `==`, ’\>\`, etc.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/1022e1f00bb1257f0ee493e0e6a1610878b9586c/src/inspect_scout/_query/column.py#L32)

``` python
class Column
```

#### Methods

in\_  
Check if value is in a list.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/1022e1f00bb1257f0ee493e0e6a1610878b9586c/src/inspect_scout/_query/column.py#L74)

``` python
def in_(self, values: list[Any]) -> Condition
```

`values` list\[Any\]  

not_in  
Check if value is not in a list.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/1022e1f00bb1257f0ee493e0e6a1610878b9586c/src/inspect_scout/_query/column.py#L78)

``` python
def not_in(self, values: list[Any]) -> Condition
```

`values` list\[Any\]  

like  
SQL LIKE pattern matching (case-sensitive).

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/1022e1f00bb1257f0ee493e0e6a1610878b9586c/src/inspect_scout/_query/column.py#L82)

``` python
def like(self, pattern: str) -> Condition
```

`pattern` str  

not_like  
SQL NOT LIKE pattern matching (case-sensitive).

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/1022e1f00bb1257f0ee493e0e6a1610878b9586c/src/inspect_scout/_query/column.py#L86)

``` python
def not_like(self, pattern: str) -> Condition
```

`pattern` str  

ilike  
PostgreSQL ILIKE pattern matching (case-insensitive).

Note: For SQLite and DuckDB, this will use LIKE with LOWER() for
case-insensitivity.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/1022e1f00bb1257f0ee493e0e6a1610878b9586c/src/inspect_scout/_query/column.py#L90)

``` python
def ilike(self, pattern: str) -> Condition
```

`pattern` str  

not_ilike  
PostgreSQL NOT ILIKE pattern matching (case-insensitive).

Note: For SQLite and DuckDB, this will use NOT LIKE with LOWER() for
case-insensitivity.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/1022e1f00bb1257f0ee493e0e6a1610878b9586c/src/inspect_scout/_query/column.py#L97)

``` python
def not_ilike(self, pattern: str) -> Condition
```

`pattern` str  

is_null  
Check if value is NULL.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/1022e1f00bb1257f0ee493e0e6a1610878b9586c/src/inspect_scout/_query/column.py#L104)

``` python
def is_null(self) -> Condition
```

is_not_null  
Check if value is not NULL.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/1022e1f00bb1257f0ee493e0e6a1610878b9586c/src/inspect_scout/_query/column.py#L108)

``` python
def is_not_null(self) -> Condition
```

between  
Check if value is between two values.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/1022e1f00bb1257f0ee493e0e6a1610878b9586c/src/inspect_scout/_query/column.py#L112)

``` python
def between(self, low: Any, high: Any) -> Condition
```

`low` Any  
Lower bound (inclusive). If None, raises ValueError.

`high` Any  
Upper bound (inclusive). If None, raises ValueError.

not_between  
Check if value is not between two values.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/1022e1f00bb1257f0ee493e0e6a1610878b9586c/src/inspect_scout/_query/column.py#L126)

``` python
def not_between(self, low: Any, high: Any) -> Condition
```

`low` Any  
Lower bound (inclusive). If None, raises ValueError.

`high` Any  
Upper bound (inclusive). If None, raises ValueError.

### Condition

WHERE clause condition that can be combined with others.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/1022e1f00bb1257f0ee493e0e6a1610878b9586c/src/inspect_scout/_query/condition.py#L42)

``` python
class Condition(BaseModel)
```

#### Attributes

`left` str \| 'Condition' \| None  
Column name (simple) or left operand (compound).

`operator` Operator \| LogicalOperator \| None  
Comparison operator (simple) or logical operator (compound).

`right` 'Condition' \| list\[ScalarValue\] \| tuple\[ScalarValue, ScalarValue\] \| ScalarValue  
Comparison value (simple) or right operand (compound).

`is_compound` bool  
True for AND/OR/NOT conditions, False for simple comparisons.

`params` list\[ScalarValue\]  
SQL parameters extracted from the condition for parameterized queries.

### Columns

Entry point for building filter expressions.

Supports both dot notation and bracket notation for accessing columns:

``` python
from inspect_scout import columns as c

c.column_name
c["column_name"]
c["nested.json.path"]
```

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/1022e1f00bb1257f0ee493e0e6a1610878b9586c/src/inspect_scout/_transcript/columns.py#L44)

``` python
class Columns
```

#### Attributes

`transcript_id` [Column](transcript.qmd#column)  
Globally unique identifier for transcript.

`source_type` [Column](transcript.qmd#column)  
Type of transcript source (e.g. “eval_log”, “weave”, etc.).

`source_id` [Column](transcript.qmd#column)  
Globally unique identifier of transcript source (e.g. ‘eval_id’ in
Inspect logs).

`source_uri` [Column](transcript.qmd#column)  
URI for source data (e.g. full path to the Inspect log file or weave
op).

`date` [Column](transcript.qmd#column)  
Date transcript was created.

`task_set` [Column](transcript.qmd#column)  
Set from which transcript task was drawn (e.g. benchmark name).

`task_id` [Column](transcript.qmd#column)  
Identifier for task (e.g. dataset sample id).

`task_repeat` [Column](transcript.qmd#column)  
Repeat for a given task id within a task set (e.g. epoch).

`agent` [Column](transcript.qmd#column)  
Agent name.

`agent_args` [Column](transcript.qmd#column)  
Agent args.

`model` [Column](transcript.qmd#column)  
Model used for eval.

`model_options` [Column](transcript.qmd#column)  
Generation options for model.

`score` [Column](transcript.qmd#column)  
Headline score value.

`success` [Column](transcript.qmd#column)  
Reduction of ‘score’ to True/False sucess.

`message_count` [Column](transcript.qmd#column)  
Messages in conversation.

`total_time` [Column](transcript.qmd#column)  
Total execution time.

`error` [Column](transcript.qmd#column)  
Error that halted exeuction.

`limit` [Column](transcript.qmd#column)  
Limit that halted execution.

### columns

Column selector for where expressions.

Typically aliased to a more compact expression (e.g. `c`) for use in
queries). For example:

``` python
from inspect_scout import columns as c
filter = c.model == "gpt-4"
filter = (c.task_set == "math") & (c.epochs > 1)
```

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/1022e1f00bb1257f0ee493e0e6a1610878b9586c/src/inspect_scout/_transcript/columns.py#L161)

``` python
columns = Columns()
```

### LogColumns

Typed column interface for Inspect log transcripts.

Provides typed properties for standard Inspect log columns while
preserving the ability to access custom fields through the base Metadata
class methods.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/1022e1f00bb1257f0ee493e0e6a1610878b9586c/src/inspect_scout/_transcript/log.py#L16)

``` python
class LogColumns(Columns)
```

#### Attributes

`transcript_id` [Column](transcript.qmd#column)  
Globally unique identifier for transcript.

`source_type` [Column](transcript.qmd#column)  
Type of transcript source (e.g. “eval_log”, “weave”, etc.).

`source_id` [Column](transcript.qmd#column)  
Globally unique identifier of transcript source (e.g. ‘eval_id’ in
Inspect logs).

`source_uri` [Column](transcript.qmd#column)  
URI for source data (e.g. full path to the Inspect log file or weave
op).

`date` [Column](transcript.qmd#column)  
Date transcript was created.

`task_set` [Column](transcript.qmd#column)  
Set from which transcript task was drawn (e.g. benchmark name).

`task_id` [Column](transcript.qmd#column)  
Identifier for task (e.g. dataset sample id).

`task_repeat` [Column](transcript.qmd#column)  
Repeat for a given task id within a task set (e.g. epoch).

`agent` [Column](transcript.qmd#column)  
Agent name.

`agent_args` [Column](transcript.qmd#column)  
Agent args.

`model` [Column](transcript.qmd#column)  
Model used for eval.

`model_options` [Column](transcript.qmd#column)  
Generation options for model.

`score` [Column](transcript.qmd#column)  
Headline score value.

`success` [Column](transcript.qmd#column)  
Reduction of ‘score’ to True/False sucess.

`message_count` [Column](transcript.qmd#column)  
Messages in conversation.

`total_time` [Column](transcript.qmd#column)  
Total execution time.

`error` [Column](transcript.qmd#column)  
Error that halted exeuction.

`limit` [Column](transcript.qmd#column)  
Limit that halted execution.

`sample_id` [Column](transcript.qmd#column)  
Unique id for sample.

`eval_id` [Column](transcript.qmd#column)  
Globally unique id for eval.

`eval_status` [Column](transcript.qmd#column)  
Status of eval.

`log` [Column](transcript.qmd#column)  
Location that the log file was read from.

`eval_tags` [Column](transcript.qmd#column)  
Tags associated with evaluation run.

`eval_metadata` [Column](transcript.qmd#column)  
Additional eval metadata.

`task_args` [Column](transcript.qmd#column)  
Task arguments.

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

`working_time` [Column](transcript.qmd#column)  
Time spent working (model generation, sandbox calls, etc.).

### log_columns

Log columns selector for where expressions.

Typically aliased to a more compact expression (e.g. `c`) for use in
queries). For example:

``` python
from inspect_scout import log_columns as c

# typed access to standard fields
filter = c.model == "gpt-4"
filter = (c.task_set == "math") & (c.epochs > 1)

# dynamic access to custom fields
filter = c["custom_field"] > 100
```

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/1022e1f00bb1257f0ee493e0e6a1610878b9586c/src/inspect_scout/_transcript/log.py#L146)

``` python
log_columns = LogColumns()
```

## Observe

### observe

Observe decorator/context manager for transcript capture.

Works as decorator (@observe, @observe(), @observe(task_set=“x”)) or
context manager (async with observe():).

Uses implicit leaf detection: the innermost observe context (one with no
children) triggers transcript write to the database. This allows nesting
observe contexts where the outer context sets shared parameters and
inner contexts represent individual transcript entries.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/1022e1f00bb1257f0ee493e0e6a1610878b9586c/src/inspect_scout/_observe/_observe.py#L100)

``` python
def observe(
    func: Callable[OP, Awaitable[OR]] | None = None,
    *,
    provider: (
        Literal["inspect", "openai", "anthropic", "google"]
        | ObserveProvider
        | Sequence[ObserveProviderName | ObserveProvider]
        | None
    ) = "inspect",
    db: str | TranscriptsDB | None = None,
    # TranscriptInfo fields (ordered to match TranscriptInfo for consistency)
    source_type: str = "observe",
    source_id: str | None = None,
    source_uri: str | None = None,
    task_set: str | None = None,
    task_id: str | None = None,
    task_repeat: int | None = None,
    agent: str | None = None,
    agent_args: dict[str, Any] | None = None,
    model: str | None = None,
    model_options: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    # Full TranscriptInfo for advanced use
    info: TranscriptInfo | None = None,
) -> Callable[OP, Awaitable[OR]] | _ObserveContextManager
```

`func` Callable\[OP, Awaitable\[OR\]\] \| None  
The async function to decorate (when used as @observe without parens).

`provider` Literal\['inspect', 'openai', 'anthropic', 'google'\] \| [ObserveProvider](transcript.qmd#observeprovider) \| Sequence\[ObserveProviderName \| [ObserveProvider](transcript.qmd#observeprovider)\] \| None  
Provider(s) for capturing LLM calls. Can be a provider name (“inspect”,
“openai”, “anthropic”, “google”), an ObserveProvider instance, or a
sequence of either. Defaults to “inspect” which captures Inspect AI
model.generate() calls. Use other providers to capture direct SDK calls.
Can only be set on root observe.

`db` str \| [TranscriptsDB](transcript.qmd#transcriptsdb) \| None  
Transcript database or path for writing. Can be a TranscriptsDB instance
or a string path (which will be passed to transcripts_db()). Only valid
on outermost observe; defaults to project transcripts directory.

`source_type` str  
Type of source for transcript. Defaults to “observe”.

`source_id` str \| None  
Globally unique ID for transcript source (e.g. eval_id).

`source_uri` str \| None  
URI for source data (e.g. log file path).

`task_set` str \| None  
Set from which transcript task was drawn (e.g. benchmark name).

`task_id` str \| None  
Identifier for task (e.g. dataset sample id).

`task_repeat` int \| None  
Repeat for a given task id within a task set (e.g. epoch).

`agent` str \| None  
Agent used to execute task.

`agent_args` dict\[str, Any\] \| None  
Arguments passed to create agent.

`model` str \| None  
Main model used by agent.

`model_options` dict\[str, Any\] \| None  
Generation options for main model.

`metadata` dict\[str, Any\] \| None  
Transcript source specific metadata (merged with parent).

`info` TranscriptInfo \| None  
Full TranscriptInfo for advanced use (fields override parent, explicit
args override info).

### observe_update

Update the current observe context’s TranscriptInfo fields.

Call this from within an @observe decorated function or observe()
context to set transcript fields after execution (e.g., score, success,
limit).

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/1022e1f00bb1257f0ee493e0e6a1610878b9586c/src/inspect_scout/_observe/_observe.py#L313)

``` python
def observe_update(
    *,
    source_type: str | None = None,
    source_id: str | None = None,
    source_uri: str | None = None,
    task_set: str | None = None,
    task_id: str | None = None,
    task_repeat: int | None = None,
    agent: str | None = None,
    agent_args: dict[str, Any] | None = None,
    model: str | None = None,
    model_options: dict[str, Any] | None = None,
    score: JsonValue | None = None,
    success: bool | None = None,
    limit: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None
```

`source_type` str \| None  
Type of source for transcript.

`source_id` str \| None  
Globally unique ID for transcript source.

`source_uri` str \| None  
URI for source data.

`task_set` str \| None  
Set from which transcript task was drawn.

`task_id` str \| None  
Identifier for task.

`task_repeat` int \| None  
Repeat for a given task id within a task set.

`agent` str \| None  
Agent used to execute task.

`agent_args` dict\[str, Any\] \| None  
Arguments passed to create agent.

`model` str \| None  
Main model used by agent.

`model_options` dict\[str, Any\] \| None  
Generation options for main model.

`score` JsonValue \| None  
Value indicating score on task.

`success` bool \| None  
Boolean reduction of score to succeeded/failed.

`limit` str \| None  
Limit that caused the task to exit.

`metadata` dict\[str, Any\] \| None  
Transcript source specific metadata (merged, not replaced).

### ObserveProvider

Protocol for LLM capture providers.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/1022e1f00bb1257f0ee493e0e6a1610878b9586c/src/inspect_scout/_observe/providers/provider.py#L22)

``` python
@runtime_checkable
class ObserveProvider(Protocol)
```

#### Methods

install  
Install hooks/patches for capturing LLM calls.

Called once per provider class. Implementations should be idempotent.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/1022e1f00bb1257f0ee493e0e6a1610878b9586c/src/inspect_scout/_observe/providers/provider.py#L26)

``` python
def install(self, emit: ObserveEmit) -> None
```

`emit` [ObserveEmit](transcript.qmd#observeemit)  
Sync callback to emit raw captured data. Call with a dict containing
request/response data. Framework handles context checking - emit() is a
no-op if not inside an observe context. The dict structure is
provider-defined and passed to build_event().

build_event  
Convert raw captured data to an Inspect Event.

Called by the framework at observe exit for each captured item. This is
where async conversion (using Inspect AI converters) happens.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/1022e1f00bb1257f0ee493e0e6a1610878b9586c/src/inspect_scout/_observe/providers/provider.py#L39)

``` python
async def build_event(self, data: dict[str, Any]) -> Event
```

`data` dict\[str, Any\]  
The dict passed to emit() during capture.

### ObserveEmit

Sync function to emit raw captured data. Called by provider wrappers.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/1022e1f00bb1257f0ee493e0e6a1610878b9586c/src/inspect_scout/_observe/providers/provider.py#L18)

``` python
ObserveEmit = Callable[[dict[str, Any]], None]
```
