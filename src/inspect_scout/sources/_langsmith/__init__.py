"""LangSmith transcript import functionality.

This module provides functions to import transcripts from LangSmith
into an Inspect Scout transcript database.

Supports traces from:
- LangChain agents/chains
- Raw OpenAI (wrap_openai)
- Raw Anthropic (wrap_anthropic)
- Raw Google (wrap_gemini)
"""

from datetime import datetime
from logging import getLogger
from typing import Any, AsyncIterator

from inspect_ai.event import ModelEvent
from inspect_ai.model._chat_message import ChatMessage

from inspect_scout._transcript.types import Transcript

from .client import (
    LANGSMITH_SOURCE_TYPE,
    get_langsmith_client,
    retry_api_call,
)
from .detection import detect_provider_format, get_model_name
from .events import runs_to_events
from .extraction import (
    extract_bool,
    extract_dict,
    extract_int,
    extract_json,
    extract_metadata,
    extract_str,
    sum_latency,
    sum_tokens,
)
from .tree import build_run_tree, flatten_tree_chronological, get_llm_runs

logger = getLogger(__name__)


async def langsmith(
    project: str | None = None,
    dataset: str | None = None,
    insights_job: str | None = None,
    cluster_id: str | None = None,
    from_time: datetime | None = None,
    to_time: datetime | None = None,
    tags: list[str] | None = None,
    filter: str | None = None,
    trace_filter: str | None = None,
    run_type: str | None = None,
    limit: int | None = None,
    api_key: str | None = None,
    api_url: str | None = None,
) -> AsyncIterator[Transcript]:
    """Read transcripts from LangSmith traces.

    Each LangSmith root run (trace) becomes one Scout transcript.
    Child runs (LLM calls, tools) become events within the transcript.

    Data sources (in priority order):
    1. `insights_job` - Fetch runs from an insights job (requires `project`)
    2. `dataset` - Fetch examples from a dataset
    3. `project` - Fetch traces from a project (default)

    Args:
        project: LangSmith project name. Required for insights_job, optional
            for dataset, used as default data source otherwise.
        dataset: LangSmith dataset name or ID. Fetches from curated evaluation
            datasets instead of project traces.
        insights_job: Insights job ID (beta API). Fetches runs associated with
            an insights clustering job. Requires `project` to be set.
        cluster_id: Optional cluster ID to filter insights job runs to a
            specific cluster. Only used with `insights_job`.
        from_time: Only fetch traces created on or after this time
        to_time: Only fetch traces created before this time
        tags: Filter by tags (all must match)
        filter: LangSmith filter string for run filtering. Can use filters
            saved from the LangSmith UI.
        trace_filter: Filter on root run attributes
        run_type: Filter by run type (llm, chain, tool, etc.)
        limit: Maximum number of transcripts to fetch
        api_key: LangSmith API key (or LANGSMITH_API_KEY env var)
        api_url: LangSmith API URL (or LANGSMITH_ENDPOINT env var)

    Yields:
        Transcript objects ready for insertion into transcript database

    Raises:
        ImportError: If langsmith package is not installed
        ValueError: If required parameters are missing
    """
    # Validate parameters
    if insights_job and not project:
        raise ValueError("'project' is required when using 'insights_job'")
    if not project and not dataset:
        raise ValueError("Either 'project' or 'dataset' must be provided")

    client = get_langsmith_client(api_key, api_url)

    # Route to appropriate data source (priority: insights_job > dataset > project)
    if insights_job:
        assert project is not None
        async for transcript in _from_insights_job(
            client, project, insights_job, cluster_id, limit
        ):
            yield transcript
    elif dataset:
        async for transcript in _from_dataset(client, dataset, project, limit):
            yield transcript
    else:
        assert project is not None
        async for transcript in _from_project(
            client,
            project,
            from_time,
            to_time,
            tags,
            filter,
            trace_filter,
            run_type,
            limit,
        ):
            yield transcript


async def _from_project(
    client: Any,
    project: str,
    from_time: datetime | None,
    to_time: datetime | None,
    tags: list[str] | None,
    filter: str | None,
    trace_filter: str | None,
    run_type: str | None,
    limit: int | None,
) -> AsyncIterator[Transcript]:
    """Fetch transcripts from a LangSmith project.

    Args:
        client: LangSmith client
        project: Project name
        from_time: Start time filter
        to_time: End time filter
        tags: Tag filters
        filter: LangSmith filter string
        trace_filter: Trace filter string
        run_type: Run type filter
        limit: Max transcripts

    Yields:
        Transcript objects
    """
    # Build query parameters for list_runs
    # We fetch root runs first (is_root=True), then get child runs for each trace
    query_params: dict[str, Any] = {
        "project_name": project,
        "is_root": True,
    }

    if from_time:
        query_params["start_time"] = from_time
    if to_time:
        # LangSmith uses end_time for the upper bound
        query_params["end_time"] = to_time
    if tags:
        # LangSmith filter for tags
        tag_filter = " and ".join(f'has(tags, "{tag}")' for tag in tags)
        if filter:
            query_params["filter"] = f"({filter}) and ({tag_filter})"
        else:
            query_params["filter"] = tag_filter
    elif filter:
        query_params["filter"] = filter
    if trace_filter:
        query_params["trace_filter"] = trace_filter
    if run_type:
        query_params["run_type"] = run_type

    # Fetch root runs using list_runs (handles pagination internally)
    count = 0
    try:

        def _list_runs(qp: dict[str, Any] = query_params) -> Any:
            return list(client.list_runs(**qp))

        root_runs = retry_api_call(_list_runs)
    except Exception as e:
        logger.error(f"Failed to list runs from project {project}: {e}")
        return

    for root_run in root_runs:
        try:
            transcript = await _trace_to_transcript(client, root_run, project)
            if transcript:
                yield transcript
                count += 1
                if limit and count >= limit:
                    return
        except Exception as e:
            run_id = getattr(root_run, "id", "unknown")
            logger.warning(f"Failed to process trace {run_id}: {e}")
            continue


async def _from_dataset(
    client: Any,
    dataset: str,
    project: str | None,
    limit: int | None,
) -> AsyncIterator[Transcript]:
    """Fetch transcripts from a LangSmith dataset.

    Args:
        client: LangSmith client
        dataset: Dataset name or ID
        project: Optional project name for context
        limit: Max transcripts

    Yields:
        Transcript objects
    """
    # List examples from dataset
    try:

        def _list_examples() -> Any:
            return list(client.list_examples(dataset_name=dataset))

        examples = retry_api_call(_list_examples)
    except Exception as e:
        logger.error(f"Failed to list examples from dataset {dataset}: {e}")
        return

    count = 0
    for example in examples:
        try:
            transcript = _example_to_transcript(example, dataset, project)
            if transcript:
                yield transcript
                count += 1
                if limit and count >= limit:
                    return
        except Exception as e:
            example_id = getattr(example, "id", "unknown")
            logger.warning(f"Failed to process example {example_id}: {e}")
            continue


async def _from_insights_job(
    client: Any,
    project: str,
    insights_job: str,
    cluster_id: str | None,
    limit: int | None,
) -> AsyncIterator[Transcript]:
    """Fetch transcripts from a LangSmith insights job.

    Uses the beta REST API to fetch runs associated with an insights
    clustering job.

    Args:
        client: LangSmith client
        project: Project name (used as session_id)
        insights_job: Insights job ID
        cluster_id: Optional cluster ID to filter to specific cluster
        limit: Max transcripts

    Yields:
        Transcript objects
    """
    # Get API URL and key from client
    api_url = (
        getattr(client, "api_url", None) or "https://api.smith.langchain.com"
    ).rstrip("/")
    api_key = getattr(client, "api_key", None)

    if not api_key:
        logger.error("API key required for insights job API")
        return

    # Import httpx for direct API calls
    try:
        import httpx
    except ImportError:
        logger.error("httpx package required for insights job API")
        return

    # Build request URL
    # API: GET /api/v1/sessions/{session_id}/insights/{job_id}/runs
    url = f"{api_url}/api/v1/sessions/{project}/insights/{insights_job}/runs"
    params: dict[str, Any] = {}
    if cluster_id:
        params["cluster_id"] = cluster_id

    headers = {
        "X-Api-Key": api_key,
        "Accept": "application/json",
    }

    # Fetch runs from insights job (with retry for transient errors)
    def _fetch_insights_runs() -> Any:
        with httpx.Client(timeout=30.0) as http_client:
            response = http_client.get(url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()

    try:
        data = retry_api_call(_fetch_insights_runs)
    except Exception as e:
        logger.error(f"Failed to fetch insights job runs: {e}")
        return

    # Extract run IDs from response
    # The response format may vary, try common structures
    run_ids: list[str] = []
    if isinstance(data, list):
        # Direct list of runs or run IDs
        for item in data:
            if isinstance(item, str):
                run_ids.append(item)
            elif isinstance(item, dict) and "run_id" in item:
                run_ids.append(item["run_id"])
            elif isinstance(item, dict) and "id" in item:
                run_ids.append(item["id"])
    elif isinstance(data, dict):
        # Wrapped response
        runs = data.get("runs") or data.get("data") or []
        for item in runs:
            if isinstance(item, str):
                run_ids.append(item)
            elif isinstance(item, dict) and "run_id" in item:
                run_ids.append(item["run_id"])
            elif isinstance(item, dict) and "id" in item:
                run_ids.append(item["id"])

    if not run_ids:
        logger.warning(f"No runs found in insights job {insights_job}")
        return

    # Fetch full run details and convert to transcripts
    count = 0
    for run_id in run_ids:
        try:
            # Fetch the run using the SDK
            def _read_run(rid: str = run_id) -> Any:
                return client.read_run(rid)

            root_run = retry_api_call(_read_run)

            transcript = await _trace_to_transcript(client, root_run, project)
            if transcript:
                # Add insights job metadata
                transcript.metadata["insights_job"] = insights_job
                if cluster_id:
                    transcript.metadata["cluster_id"] = cluster_id
                yield transcript
                count += 1
                if limit and count >= limit:
                    return
        except Exception as e:
            logger.warning(f"Failed to process run {run_id}: {e}")
            continue


async def _trace_to_transcript(
    client: Any,
    root_run: Any,
    project: str,
) -> Transcript | None:
    """Convert a LangSmith trace (root run + children) to a Scout Transcript.

    Args:
        client: LangSmith client for fetching child runs
        root_run: LangSmith root run object
        project: Project name for metadata

    Returns:
        Transcript object or None if trace has no valid data
    """
    trace_id = str(getattr(root_run, "trace_id", None) or getattr(root_run, "id", ""))

    # Fetch all runs in the trace
    try:

        def _get_trace_runs() -> Any:
            return list(client.list_runs(trace_id=trace_id))

        all_runs = retry_api_call(_get_trace_runs)
    except Exception as e:
        logger.warning(f"Failed to fetch runs for trace {trace_id}: {e}")
        # Fall back to just the root run
        all_runs = [root_run]

    if not all_runs:
        return None

    # Build tree and flatten chronologically
    tree = build_run_tree(all_runs)
    ordered_runs = flatten_tree_chronological(tree)

    # Convert runs to events
    events = await runs_to_events(ordered_runs)

    # Get LLM runs for message extraction and metadata
    llm_runs = get_llm_runs(ordered_runs)

    # Build messages from the last LLM run's input + output
    messages: list[ChatMessage] = []
    if llm_runs:
        model_events = [e for e in events if isinstance(e, ModelEvent)]
        if model_events:
            last_model = model_events[-1]
            messages = list(last_model.input)
            if last_model.output and last_model.output.message:
                messages.append(last_model.output.message)

    # Extract metadata from root run
    metadata = extract_metadata(root_run)
    task_repeat = extract_int("task_repeat", metadata)
    agent = extract_str("agent", metadata)
    agent_args = extract_dict("agent_args", metadata)
    model_options = extract_dict("model_options", metadata)
    error = extract_str("error", metadata) or (
        str(root_run.error) if getattr(root_run, "error", None) else None
    )
    limit_val = extract_str("limit", metadata)
    score = extract_json("score", metadata)
    success = extract_bool("success", metadata)

    # Get model name
    model_name = get_model_name(llm_runs[0]) if llm_runs else None

    # Construct source URI
    run_id = getattr(root_run, "id", "unknown")
    base_url = (
        getattr(client, "api_url", None) or "https://smith.langchain.com"
    ).rstrip("/")
    source_uri = f"{base_url}/o/default/projects/p/{project}/r/{run_id}"

    return Transcript(
        transcript_id=str(run_id),
        source_type=LANGSMITH_SOURCE_TYPE,
        source_id=project,
        source_uri=source_uri,
        date=str(root_run.start_time)
        if getattr(root_run, "start_time", None)
        else None,
        task_set=project,
        task_id=getattr(root_run, "name", None),
        task_repeat=task_repeat,
        agent=agent,
        agent_args=agent_args,
        model=model_name,
        model_options=model_options,
        score=score,
        success=success,
        message_count=len(messages),
        total_tokens=sum_tokens(llm_runs),
        total_time=sum_latency(ordered_runs),
        error=error,
        limit=limit_val,
        messages=messages,
        events=events,
        metadata=metadata,
    )


def _example_to_transcript(
    example: Any,
    dataset: str,
    project: str | None,
) -> Transcript | None:
    """Convert a LangSmith dataset example to a Scout Transcript.

    Dataset examples contain inputs/outputs but not full run traces.

    Args:
        example: LangSmith example object
        dataset: Dataset name
        project: Optional project name

    Returns:
        Transcript object or None
    """
    from inspect_ai.model._chat_message import ChatMessageAssistant, ChatMessageUser

    example_id = str(getattr(example, "id", ""))
    inputs = getattr(example, "inputs", {}) or {}
    outputs = getattr(example, "outputs", {}) or {}

    # Build simple message list from inputs/outputs
    messages: list[ChatMessage] = []

    # Extract input message
    if "input" in inputs:
        messages.append(ChatMessageUser(content=str(inputs["input"])))
    elif "messages" in inputs:
        # Handle message list in inputs
        for msg in inputs["messages"]:
            if isinstance(msg, dict):
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role == "user":
                    messages.append(ChatMessageUser(content=str(content)))
                elif role == "assistant":
                    messages.append(ChatMessageAssistant(content=str(content)))

    # Extract output message
    if "output" in outputs:
        messages.append(ChatMessageAssistant(content=str(outputs["output"])))
    elif "response" in outputs:
        messages.append(ChatMessageAssistant(content=str(outputs["response"])))

    if not messages:
        return None

    # Extract metadata
    metadata: dict[str, Any] = {}
    if getattr(example, "metadata", None):
        metadata.update(example.metadata)

    return Transcript(
        transcript_id=example_id,
        source_type=LANGSMITH_SOURCE_TYPE,
        source_id=dataset,
        source_uri=None,  # Dataset examples don't have direct URLs
        date=str(example.created_at) if hasattr(example, "created_at") else None,
        task_set=project or dataset,
        task_id=dataset,
        task_repeat=None,
        agent=None,
        agent_args=None,
        model=None,
        model_options=None,
        score=None,
        success=None,
        message_count=len(messages),
        total_tokens=None,
        total_time=None,
        error=None,
        limit=None,
        messages=messages,
        events=[],
        metadata=metadata,
    )


# Re-exports
__all__ = ["langsmith", "LANGSMITH_SOURCE_TYPE", "detect_provider_format"]
