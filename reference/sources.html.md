# Sources – Inspect Scout

### phoenix

Read transcripts from [Arize Phoenix](https://phoenix.arize.com/) traces.

Each Phoenix trace (collection of spans with same trace_id) becomes one Scout transcript. Child spans (LLM calls, tools) become events within the transcript.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/8a6325fef4cc5070d2449ba707f7961d90d32b5c/src/inspect_scout/sources/_phoenix/__init__.py#L43)

``` python
async def phoenix(
    project: str | None = None,
    from_time: datetime | None = None,
    to_time: datetime | None = None,
    trace_id: str | list[str] | None = None,
    session_id: str | list[str] | None = None,
    tags: list[str] | None = None,
    metadata: dict[str, str] | None = None,
    limit: int | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
) -> AsyncIterator[Transcript]
```

`project` str \| None  
Phoenix project name or ID. Required for fetching spans.

`from_time` datetime \| None  
Only fetch traces created on or after this time

`to_time` datetime \| None  
Only fetch traces created before this time

`trace_id` str \| list\[str\] \| None  
Fetch specific trace(s) by ID (single string or list)

`session_id` str \| list\[str\] \| None  
Filter to traces belonging to specific session(s) (matches `session.id` attribute on root span)

`tags` list\[str\] \| None  
Filter by tags on root span (all must match; stored in `tag.tags` attribute)

`metadata` dict\[str, str\] \| None  
Filter by metadata key-value pairs on root span (all must match; stored in `metadata.*` attributes)

`limit` int \| None  
Maximum number of transcripts to fetch

`api_key` str \| None  
Phoenix API key (or PHOENIX_API_KEY env var)

`base_url` str \| None  
Phoenix base URL (or PHOENIX_COLLECTOR_ENDPOINT env var)

### langsmith

Read transcripts from [LangSmith](https://smith.langchain.com/) traces.

Each LangSmith root run (trace) becomes one Scout transcript. Child runs (LLM calls, tools) become events within the transcript.

Data sources:

- `project` - Import traces from a project (default)
- `dataset` - Import examples from a dataset

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/8a6325fef4cc5070d2449ba707f7961d90d32b5c/src/inspect_scout/sources/_langsmith/__init__.py#L49)

``` python
async def langsmith(
    project: str | None = None,
    dataset: str | None = None,
    from_time: datetime | None = None,
    to_time: datetime | None = None,
    tags: list[str] | None = None,
    filter: str | None = None,
    trace_filter: str | None = None,
    run_type: str | None = None,
    limit: int | None = None,
    api_key: str | None = None,
    api_url: str | None = None,
) -> AsyncIterator[Transcript]
```

`project` str \| None  
LangSmith project name. Optional for dataset, used as default data source otherwise.

`dataset` str \| None  
LangSmith dataset name or ID. Fetches from curated evaluation datasets instead of project traces.

`from_time` datetime \| None  
Only fetch traces created on or after this time

`to_time` datetime \| None  
Only fetch traces created before this time

`tags` list\[str\] \| None  
Filter by tags (all must match)

`filter` str \| None  
LangSmith filter string for run filtering. Can use filters saved from the LangSmith UI.

`trace_filter` str \| None  
Filter on root run attributes

`run_type` str \| None  
Filter by run type (llm, chain, tool, etc.)

`limit` int \| None  
Maximum number of transcripts to fetch

`api_key` str \| None  
LangSmith API key (or LANGSMITH_API_KEY env var)

`api_url` str \| None  
LangSmith API URL (or LANGSMITH_ENDPOINT env var)

### logfire

Read transcripts from [Logfire](https://logfire.pydantic.dev/) traces.

Each Logfire trace (collection of spans with same trace_id) becomes one Scout transcript. Child spans (LLM calls, tools) become events within the transcript.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/8a6325fef4cc5070d2449ba707f7961d90d32b5c/src/inspect_scout/sources/_logfire/__init__.py#L45)

``` python
async def logfire(
    project: str | None = None,
    from_time: datetime | None = None,
    to_time: datetime | None = None,
    filter: str | None = None,
    trace_id: str | None = None,
    limit: int | None = None,
    read_token: str | None = None,
) -> AsyncIterator[Transcript]
```

`project` str \| None  
Logfire project name in format “org/project”. If not provided, queries across all accessible projects.

`from_time` datetime \| None  
Only fetch traces created on or after this time

`to_time` datetime \| None  
Only fetch traces created before this time

`filter` str \| None  
SQL WHERE fragment for additional filtering (e.g., “attributes-\>\>‘gen_ai.request.model’ = ‘gpt-4o’”)

`trace_id` str \| None  
Fetch a specific trace by ID instead of querying

`limit` int \| None  
Maximum number of transcripts to fetch

`read_token` str \| None  
Logfire read token (or LOGFIRE_READ_TOKEN env var). Generate from Logfire dashboard Settings \> Read Tokens.

### weave

Read transcripts from [W&B Weave](https://wandb.ai/site/weave) traces.

Each Weave trace (root call + children) becomes one Scout transcript. Child calls (LLM calls, tools) become events within the transcript.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/8a6325fef4cc5070d2449ba707f7961d90d32b5c/src/inspect_scout/sources/_weave/__init__.py#L49)

``` python
async def weave(
    project: str,
    from_time: datetime | None = None,
    to_time: datetime | None = None,
    filter: dict[str, Any] | None = None,
    limit: int | None = None,
    api_key: str | None = None,
) -> AsyncIterator[Transcript]
```

`project` str  
W&B project name in format “entity/project”

`from_time` datetime \| None  
Only fetch traces created on or after this time

`to_time` datetime \| None  
Only fetch traces created before this time

`filter` dict\[str, Any\] \| None  
Dictionary of filters to apply to call query

`limit` int \| None  
Maximum number of transcripts to fetch

`api_key` str \| None  
W&B API key (or WANDB_API_KEY env var)

### claude_code

Read transcripts from Claude Code sessions.

Each Claude Code session can contain multiple conversations separated by /clear commands. Each conversation becomes one Scout transcript.

When Claude Code enters plan mode and executes a plan, it creates separate session files that share the same slug. These related sessions are merged into a single transcript.

[Source](https://github.com/meridianlabs-ai/inspect_scout/blob/8a6325fef4cc5070d2449ba707f7961d90d32b5c/src/inspect_scout/sources/_claude_code/transcripts.py#L63)

``` python
async def claude_code(
    path: str | PathLike[str] | None = None,
    session_id: str | None = None,
    from_time: datetime | None = None,
    to_time: datetime | None = None,
    limit: int | None = None,
) -> AsyncIterator["Transcript"]
```

`path` str \| PathLike\[str\] \| None  
Path to Claude Code project directory or specific session file. If None, scans all projects in ~/.claude/projects/

`session_id` str \| None  
Specific session UUID to import

`from_time` datetime \| None  
Only fetch sessions modified on or after this time

`to_time` datetime \| None  
Only fetch sessions modified before this time

`limit` int \| None  
Maximum number of transcripts to yield
