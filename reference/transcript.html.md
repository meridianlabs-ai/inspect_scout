# Transcript API


## Reading

### transcripts_from

Read transcripts for scanning.

Transcripts may be stored in a `TranscriptDB` or may be Inspect eval
logs.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/907490a3fd8c890fbcf68fbfe539065e9cfcf395/src/inspect_scout/_transcript/factory.py#L19)

``` python
def transcripts_from(location: str | Logs) -> Transcripts
```

`location` str \| Logs  
Transcripts location. Either a path to a transcript database or path(s)
to Inspect eval logs.

### Transcript

Transcript info and transcript content (messages and events).

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/907490a3fd8c890fbcf68fbfe539065e9cfcf395/src/inspect_scout/_transcript/types.py#L100)

``` python
class Transcript(TranscriptInfo)
```

#### Attributes

`messages` list\[ChatMessage\]  
Main message thread.

`events` list\[Event\]  
Events from transcript.

### Transcripts

Collection of transcripts for scanning.

Transcript collections can be filtered using the `where()`, `limit()`,
and ’shuffle()\` methods. The transcripts are not modified in place so
the filtered transcripts should be referenced via the return value. For
example:

``` python
from inspect_scout import transcripts, columns as c

transcripts = transcripts_from("./logs")
transcripts = transcripts.where(c.task_set == "cybench")
```

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/907490a3fd8c890fbcf68fbfe539065e9cfcf395/src/inspect_scout/_transcript/transcripts.py#L70)

``` python
class Transcripts(abc.ABC)
```

#### Methods

where  
Filter the transcript collection by a `Condition`.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/907490a3fd8c890fbcf68fbfe539065e9cfcf395/src/inspect_scout/_transcript/transcripts.py#L89)

``` python
def where(self, condition: Condition) -> "Transcripts"
```

`condition` [Condition](transcript.qmd#condition)  
Filter condition.

for_validation  
Filter transcripts to only those with IDs matching validation cases.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/907490a3fd8c890fbcf68fbfe539065e9cfcf395/src/inspect_scout/_transcript/transcripts.py#L102)

``` python
def for_validation(
    self, validation: ValidationSet | dict[str, ValidationSet]
) -> "Transcripts"
```

`validation` [ValidationSet](results.qmd#validationset) \| dict\[str, [ValidationSet](results.qmd#validationset)\]  
Validation object containing cases with target IDs.

limit  
Limit the number of transcripts processed.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/907490a3fd8c890fbcf68fbfe539065e9cfcf395/src/inspect_scout/_transcript/transcripts.py#L165)

``` python
def limit(self, n: int) -> "Transcripts"
```

`n` int  
Limit on transcripts.

shuffle  
Shuffle the order of transcripts.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/907490a3fd8c890fbcf68fbfe539065e9cfcf395/src/inspect_scout/_transcript/transcripts.py#L178)

``` python
def shuffle(self, seed: int | None = None) -> "Transcripts"
```

`seed` int \| None  
Random seed for shuffling.

reader  
Read the selected transcripts.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/907490a3fd8c890fbcf68fbfe539065e9cfcf395/src/inspect_scout/_transcript/transcripts.py#L191)

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

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/907490a3fd8c890fbcf68fbfe539065e9cfcf395/src/inspect_scout/_transcript/transcripts.py#L202)

``` python
@staticmethod
@abc.abstractmethod
def from_snapshot(snapshot: ScanTranscripts) -> "Transcripts"
```

`snapshot` [ScanTranscripts](scanning.qmd#scantranscripts)  

### TranscriptsReader

Read transcripts based on a `TranscriptsQuery`.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/907490a3fd8c890fbcf68fbfe539065e9cfcf395/src/inspect_scout/_transcript/transcripts.py#L16)

``` python
class TranscriptsReader(abc.ABC)
```

#### Methods

index  
Index of `TranscriptInfo` for the collection.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/907490a3fd8c890fbcf68fbfe539065e9cfcf395/src/inspect_scout/_transcript/transcripts.py#L32)

``` python
@abc.abstractmethod
def index(self) -> AsyncIterator[TranscriptInfo]
```

read  
Read transcript content.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/907490a3fd8c890fbcf68fbfe539065e9cfcf395/src/inspect_scout/_transcript/transcripts.py#L37)

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

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/907490a3fd8c890fbcf68fbfe539065e9cfcf395/src/inspect_scout/_transcript/database/factory.py#L12)

``` python
def transcripts_db(location: str) -> TranscriptsDB
```

`location` str  
Database location (e.g. directory or S3 bucket).

### TranscriptsDB

Database of transcripts.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/907490a3fd8c890fbcf68fbfe539065e9cfcf395/src/inspect_scout/_transcript/database/database.py#L16)

``` python
class TranscriptsDB(abc.ABC)
```

#### Methods

\_\_init\_\_  
Create a transcripts database.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/907490a3fd8c890fbcf68fbfe539065e9cfcf395/src/inspect_scout/_transcript/database/database.py#L19)

``` python
def __init__(self, location: str) -> None
```

`location` str  
Database location (e.g. local or S3 file path)

connect  
Connect to transcripts database.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/907490a3fd8c890fbcf68fbfe539065e9cfcf395/src/inspect_scout/_transcript/database/database.py#L27)

``` python
@abc.abstractmethod
async def connect(self) -> None
```

disconnect  
Disconnect to transcripts database.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/907490a3fd8c890fbcf68fbfe539065e9cfcf395/src/inspect_scout/_transcript/database/database.py#L32)

``` python
@abc.abstractmethod
async def disconnect(self) -> None
```

insert  
Insert transcripts into database.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/907490a3fd8c890fbcf68fbfe539065e9cfcf395/src/inspect_scout/_transcript/database/database.py#L52)

``` python
@abc.abstractmethod
async def insert(
    self,
    transcripts: Iterable[Transcript]
    | AsyncIterable[Transcript]
    | Transcripts
    | TranscriptsSource,
) -> None
```

`transcripts` Iterable\[[Transcript](transcript.qmd#transcript)\] \| AsyncIterable\[[Transcript](transcript.qmd#transcript)\] \| [Transcripts](transcript.qmd#transcripts) \| [TranscriptsSource](transcript.qmd#transcriptssource)  
Transcripts to insert (iterable, async iterable, or source).

transcript_ids  
Get transcript IDs matching conditions.

Optimized method that returns only transcript IDs without loading full
metadata. Default implementation uses select(), but subclasses can
override for better performance.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/907490a3fd8c890fbcf68fbfe539065e9cfcf395/src/inspect_scout/_transcript/database/database.py#L67)

``` python
@abc.abstractmethod
async def transcript_ids(
    self,
    where: list[Condition] | None = None,
    limit: int | None = None,
    shuffle: bool | int = False,
) -> dict[str, str | None]
```

`where` list\[[Condition](transcript.qmd#condition)\] \| None  
Condition(s) to filter by.

`limit` int \| None  
Maximum number to return.

`shuffle` bool \| int  
Randomly shuffle results (pass `int` for reproducible seed).

select  
Select transcripts matching a condition.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/907490a3fd8c890fbcf68fbfe539065e9cfcf395/src/inspect_scout/_transcript/database/database.py#L90)

``` python
@abc.abstractmethod
def select(
    self,
    where: list[Condition] | None = None,
    limit: int | None = None,
    shuffle: bool | int = False,
) -> AsyncIterator[TranscriptInfo]
```

`where` list\[[Condition](transcript.qmd#condition)\] \| None  
Condition(s) to select for.

`limit` int \| None  
Maximum number to select.

`shuffle` bool \| int  
Randomly shuffle transcripts selected (pass `int` for reproducible
seed).

read  
Read transcript content.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/907490a3fd8c890fbcf68fbfe539065e9cfcf395/src/inspect_scout/_transcript/database/database.py#L106)

``` python
@abc.abstractmethod
async def read(self, t: TranscriptInfo, content: TranscriptContent) -> Transcript
```

`t` TranscriptInfo  
Transcript to read.

`content` TranscriptContent  
Content to read (messages, events, etc.)

### TranscriptsSource

Async iterator of transcripts.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/907490a3fd8c890fbcf68fbfe539065e9cfcf395/src/inspect_scout/_transcript/database/source/source.py#L10)

``` python
class TranscriptsSource(Protocol):
    def __call__(self) -> AsyncIterator[Transcript]
```

## Filtering

### Column

Database column with comparison operators.

Supports various predicate functions including `like()`, `not_like()`,
`between()`, etc. Additionally supports standard python equality and
comparison operators (e.g. `==`, ’\>\`, etc.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/907490a3fd8c890fbcf68fbfe539065e9cfcf395/src/inspect_scout/_transcript/columns.py#L521)

``` python
class Column
```

#### Methods

in\_  
Check if value is in a list.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/907490a3fd8c890fbcf68fbfe539065e9cfcf395/src/inspect_scout/_transcript/columns.py#L563)

``` python
def in_(self, values: list[Any]) -> Condition
```

`values` list\[Any\]  

not_in  
Check if value is not in a list.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/907490a3fd8c890fbcf68fbfe539065e9cfcf395/src/inspect_scout/_transcript/columns.py#L567)

``` python
def not_in(self, values: list[Any]) -> Condition
```

`values` list\[Any\]  

like  
SQL LIKE pattern matching (case-sensitive).

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/907490a3fd8c890fbcf68fbfe539065e9cfcf395/src/inspect_scout/_transcript/columns.py#L571)

``` python
def like(self, pattern: str) -> Condition
```

`pattern` str  

not_like  
SQL NOT LIKE pattern matching (case-sensitive).

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/907490a3fd8c890fbcf68fbfe539065e9cfcf395/src/inspect_scout/_transcript/columns.py#L575)

``` python
def not_like(self, pattern: str) -> Condition
```

`pattern` str  

ilike  
PostgreSQL ILIKE pattern matching (case-insensitive).

Note: For SQLite and DuckDB, this will use LIKE with LOWER() for
case-insensitivity.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/907490a3fd8c890fbcf68fbfe539065e9cfcf395/src/inspect_scout/_transcript/columns.py#L579)

``` python
def ilike(self, pattern: str) -> Condition
```

`pattern` str  

not_ilike  
PostgreSQL NOT ILIKE pattern matching (case-insensitive).

Note: For SQLite and DuckDB, this will use NOT LIKE with LOWER() for
case-insensitivity.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/907490a3fd8c890fbcf68fbfe539065e9cfcf395/src/inspect_scout/_transcript/columns.py#L586)

``` python
def not_ilike(self, pattern: str) -> Condition
```

`pattern` str  

is_null  
Check if value is NULL.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/907490a3fd8c890fbcf68fbfe539065e9cfcf395/src/inspect_scout/_transcript/columns.py#L593)

``` python
def is_null(self) -> Condition
```

is_not_null  
Check if value is not NULL.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/907490a3fd8c890fbcf68fbfe539065e9cfcf395/src/inspect_scout/_transcript/columns.py#L597)

``` python
def is_not_null(self) -> Condition
```

between  
Check if value is between two values.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/907490a3fd8c890fbcf68fbfe539065e9cfcf395/src/inspect_scout/_transcript/columns.py#L601)

``` python
def between(self, low: Any, high: Any) -> Condition
```

`low` Any  
Lower bound (inclusive). If None, raises ValueError.

`high` Any  
Upper bound (inclusive). If None, raises ValueError.

not_between  
Check if value is not between two values.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/907490a3fd8c890fbcf68fbfe539065e9cfcf395/src/inspect_scout/_transcript/columns.py#L615)

``` python
def not_between(self, low: Any, high: Any) -> Condition
```

`low` Any  
Lower bound (inclusive). If None, raises ValueError.

`high` Any  
Upper bound (inclusive). If None, raises ValueError.

### Condition

WHERE clause condition that can be combined with others.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/907490a3fd8c890fbcf68fbfe539065e9cfcf395/src/inspect_scout/_transcript/columns.py#L64)

``` python
class Condition
```

#### Methods

to_sql  
Generate SQL WHERE clause and parameters.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/907490a3fd8c890fbcf68fbfe539065e9cfcf395/src/inspect_scout/_transcript/columns.py#L116)

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

### Columns

Entry point for building filter expressions.

> [!NOTE]
>
> Note that the `Columns` class is available only in the development
> version of Inspect Scout. Install the development version from GitHub
> with:
>
> ``` python
> pip install git+https://github.com/meridianlabs-ai/inspect_scout
> ```

Supports both dot notation and bracket notation for accessing columns:

``` python
from inspect_scout import columns as c

c.column_name
c["column_name"]
c["nested.json.path"]
```

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/907490a3fd8c890fbcf68fbfe539065e9cfcf395/src/inspect_scout/_transcript/columns.py#L630)

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

`score` [Column](transcript.qmd#column)  
Headline score value.

`success` [Column](transcript.qmd#column)  
Reduction of ‘score’ to True/False sucess.

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

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/907490a3fd8c890fbcf68fbfe539065e9cfcf395/src/inspect_scout/_transcript/columns.py#L745)

``` python
columns = Columns()
```

### LogColumns

Typed column interface for Inspect log transcripts.

> [!NOTE]
>
> Note that the `LogColumns` class is available only in the development
> version of Inspect Scout. Install the development version from GitHub
> with:
>
> ``` python
> pip install git+https://github.com/meridianlabs-ai/inspect_scout
> ```

Provides typed properties for standard Inspect log columns while
preserving the ability to access custom fields through the base Metadata
class methods.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/907490a3fd8c890fbcf68fbfe539065e9cfcf395/src/inspect_scout/_transcript/log.py#L16)

``` python
class LogColumns(Columns)
```

#### Attributes

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

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/907490a3fd8c890fbcf68fbfe539065e9cfcf395/src/inspect_scout/_transcript/log.py#L154)

``` python
log_columns = LogColumns()
```
