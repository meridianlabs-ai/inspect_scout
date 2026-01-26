"""Core implementation of the observe decorator and context manager."""

import inspect
import logging
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from functools import wraps
from typing import (
    Any,
    AsyncIterator,
    Awaitable,
    Callable,
    Literal,
    Sequence,
    overload,
)

from inspect_ai.event._model import ModelEvent
from inspect_ai.log._transcript import Transcript as InspectTranscript
from inspect_ai.log._transcript import init_transcript
from inspect_ai.model import ChatMessage
from inspect_ai.model._model_output import ModelOutput
from pydantic import JsonValue

from inspect_scout._project import read_project
from inspect_scout._transcript.database.database import TranscriptsDB
from inspect_scout._transcript.database.factory import transcripts_db
from inspect_scout._transcript.types import Transcript, TranscriptInfo

from .context import (
    OP,
    OR,
    ObserveContext,
    _current_context,
    _ObserveContextManager,
)
from .providers import (
    ObserveProvider,
    ObserveProviderName,
    get_provider_instance,
    install_providers,
)

logger = logging.getLogger(__name__)


async def _process_pending_captures(ctx: ObserveContext) -> None:
    """Process pending SDK captures and append events to transcript.

    Args:
        ctx: The observe context containing pending captures.
    """
    for data, provider_key in ctx.pending_captures:
        provider_instance = get_provider_instance(provider_key)
        if provider_instance is not None:
            try:
                event = await provider_instance.build_event(data)
                ctx.inspect_transcript._events.append(event)
            except Exception as e:
                logger.warning(f"Failed to build event from {provider_key}: {e}")
    ctx.pending_captures.clear()


# @observe (bare decorator without parens)
@overload
def observe(
    func: Callable[OP, Awaitable[OR]],
) -> Callable[OP, Awaitable[OR]]: ...


# @observe() or async with observe() (with optional keyword args)
@overload
def observe(
    func: None = None,
    *,
    provider: (
        Literal["inspect", "openai", "anthropic", "google"]
        | ObserveProvider
        | Sequence[ObserveProviderName | ObserveProvider]
        | None
    ) = ...,
    db: str | TranscriptsDB | None = None,
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
    info: TranscriptInfo | None = None,
) -> _ObserveContextManager: ...


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
) -> Callable[OP, Awaitable[OR]] | _ObserveContextManager:
    """Observe decorator/context manager for transcript capture.

    Works as decorator (@observe, @observe(), @observe(task_set="x"))
    or context manager (async with observe():).

    Uses implicit leaf detection: the innermost observe context (one with no
    children) triggers transcript write to the database. This allows nesting
    observe contexts where the outer context sets shared parameters and inner
    contexts represent individual transcript entries.

    Args:
        func: The async function to decorate (when used as @observe without parens).
        provider: Provider(s) for capturing LLM calls. Can be a provider name
            ("inspect", "openai", "anthropic", "google"), an ObserveProvider
            instance, or a sequence of either. Defaults to "inspect" which
            captures Inspect AI model.generate() calls. Use other providers
            to capture direct SDK calls. Can only be set on root observe.
        db: Transcript database or path for writing. Can be a TranscriptsDB instance
            or a string path (which will be passed to transcripts_db()). Only valid
            on outermost observe; defaults to project transcripts directory.
        source_type: Type of source for transcript. Defaults to "observe".
        source_id: Globally unique ID for transcript source (e.g. eval_id).
        source_uri: URI for source data (e.g. log file path).
        task_set: Set from which transcript task was drawn (e.g. benchmark name).
        task_id: Identifier for task (e.g. dataset sample id).
        task_repeat: Repeat for a given task id within a task set (e.g. epoch).
        agent: Agent used to execute task.
        agent_args: Arguments passed to create agent.
        model: Main model used by agent.
        model_options: Generation options for main model.
        metadata: Transcript source specific metadata (merged with parent).
        info: Full TranscriptInfo for advanced use (fields override parent,
            explicit args override info).

    Returns:
        When used as decorator: the decorated async function.
        When used as context manager: an async context manager.

    Raises:
        TypeError: If used to decorate a non-async function.
        ValueError: If db or provider is specified on a non-root observe.

    Example:
        ```python
        # As decorator with Inspect AI capture (default)
        @observe(task_set="eval", task_id="case_1")
        async def run_case():
            response = await model.generate([ChatMessageUser(content="Hello")])
            observe_update(score=0.95, success=True)
            return response

        # Capture OpenAI SDK calls directly
        @observe(provider="openai", task_set="eval")
        async def run_openai():
            client = openai.AsyncOpenAI()
            response = await client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": "Hello"}]
            )
            return response

        # Capture multiple providers
        async with observe(provider=["openai", "anthropic"], task_set="eval"):
            # Both OpenAI and Anthropic calls will be captured
            ...
        ```
    """

    @asynccontextmanager
    async def _observe_async() -> AsyncIterator[ObserveContext]:
        parent = _current_context.get()
        is_root = parent is None

        # Validate: db can only be set on root
        if db is not None and not is_root:
            raise ValueError("'db' can only be specified on the outermost observe")

        # Validate: provider can only be set on root (non-default value)
        if provider is not None and provider != "inspect" and not is_root:
            raise ValueError(
                "'provider' can only be specified on the outermost observe"
            )

        # Install providers at root (idempotent, tracked by class name)
        if is_root and provider is not None:
            install_providers(provider)

        # Resolve db: explicit (root only) or inherit from parent or project default
        if is_root:
            if isinstance(db, str):
                resolved_db = transcripts_db(db)
            else:
                resolved_db = db or _get_project_db()
            # Connect to database at root
            await resolved_db.connect()
        else:
            assert parent is not None
            resolved_db = parent.db

        # Merge TranscriptInfo: parent -> info param -> explicit kwargs
        merged_info = _merge_transcript_info(
            parent.info if parent else None,
            info,
            source_type=source_type,
            source_id=source_id,
            source_uri=source_uri,
            task_set=task_set,
            task_id=task_id,
            task_repeat=task_repeat,
            agent=agent,
            agent_args=agent_args,
            model=model,
            model_options=model_options,
            metadata=metadata,
        )

        # Create Inspect AI transcript for event capture
        inspect_transcript = InspectTranscript()
        init_transcript(inspect_transcript)

        ctx = ObserveContext(
            info=merged_info,
            inspect_transcript=inspect_transcript,
            db=resolved_db,
            is_root=is_root,
            parent=parent,
        )

        if parent:
            parent.had_children = True

        start_time = time.time()
        error: Exception | None = None

        token = _current_context.set(ctx)
        try:
            yield ctx
        except (KeyboardInterrupt, SystemExit, GeneratorExit):
            # Let abort exceptions propagate - these should stop processing
            raise
        except Exception as e:
            # Capture error for transcript - suppress to continue batch run
            error = e
            logger.warning(f"Error in observe context (saved to transcript): {e}")
        finally:
            # CRITICAL: Reset context first to ensure it always happens
            _current_context.reset(token)

            try:
                await _process_pending_captures(ctx)

                # Insert transcript immediately if leaf node (no children ran)
                if not ctx.had_children:
                    transcript = _build_transcript(ctx, start_time, error)
                    await ctx.db.insert([transcript], commit=False)

                # If we're the root, commit (compact + index)
                if ctx.is_root:
                    try:
                        await ctx.db.commit()
                    except Exception as e:
                        logger.warning(f"Commit failed (transcripts saved): {e}")
            except Exception as e:
                logger.warning(f"Failed to save transcript: {e}")
            finally:
                # CRITICAL: Always disconnect if root, even on errors
                if ctx.is_root:
                    try:
                        await ctx.db.disconnect()
                    except Exception:
                        pass  # Best effort - don't mask other errors

    if func is not None:
        # Called as @observe without parens - must be async function
        if not inspect.iscoroutinefunction(func):
            raise TypeError("@observe can only decorate async functions")

        @wraps(func)
        async def async_wrapper(*args: OP.args, **kwargs: OP.kwargs) -> OR:
            async with _observe_async():
                return await func(*args, **kwargs)

        return async_wrapper

    # Return wrapper that works as both context manager and decorator
    return _ObserveContextManager(_observe_async)


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
) -> None:
    """Update the current observe context's TranscriptInfo fields.

    Call this from within an @observe decorated function or observe() context
    to set transcript fields after execution (e.g., score, success, limit).

    Args:
        source_type: Type of source for transcript.
        source_id: Globally unique ID for transcript source.
        source_uri: URI for source data.
        task_set: Set from which transcript task was drawn.
        task_id: Identifier for task.
        task_repeat: Repeat for a given task id within a task set.
        agent: Agent used to execute task.
        agent_args: Arguments passed to create agent.
        model: Main model used by agent.
        model_options: Generation options for main model.
        score: Value indicating score on task.
        success: Boolean reduction of score to succeeded/failed.
        limit: Limit that caused the task to exit.
        metadata: Transcript source specific metadata (merged, not replaced).

    Raises:
        RuntimeError: If called outside an observe context.

    Example:
        ```python
        @observe(task_set="eval")
        async def run_case():
            result = await llm_call()
            score = evaluate(result)
            observe_update(score=score, success=score > 0.8)
            return result
        ```
    """
    ctx = _current_context.get()
    if ctx is None:
        raise RuntimeError("observe_update() called outside of an observe context")

    # Update fields on the context's info (only non-None values)
    updates = {
        "source_type": source_type,
        "source_id": source_id,
        "source_uri": source_uri,
        "task_set": task_set,
        "task_id": task_id,
        "task_repeat": task_repeat,
        "agent": agent,
        "agent_args": agent_args,
        "model": model,
        "model_options": model_options,
        "score": score,
        "success": success,
        "limit": limit,
    }
    for field_name, value in updates.items():
        if value is not None:
            setattr(ctx.info, field_name, value)

    # Metadata is merged, not replaced
    if metadata is not None:
        if ctx.info.metadata is None:
            ctx.info.metadata = {}
        ctx.info.metadata.update(metadata)


def _get_project_db() -> TranscriptsDB:
    """Get TranscriptsDB from project config.

    Falls back to './transcripts' in the current working directory if no
    transcripts directory is configured in the project.
    """
    project = read_project()
    location = (
        project.transcripts if project.transcripts is not None else "./transcripts"
    )
    return transcripts_db(location)


def _merge_transcript_info(
    parent_info: TranscriptInfo | None,
    explicit_info: TranscriptInfo | None,
    **kwargs: Any,
) -> TranscriptInfo:
    """Merge TranscriptInfo with precedence: kwargs > explicit_info > parent_info.

    Args:
        parent_info: Info from parent observe context (lowest precedence).
        explicit_info: Explicit TranscriptInfo parameter (middle precedence).
        **kwargs: Individual field overrides (highest precedence).

    Returns:
        Merged TranscriptInfo.
    """
    # Start with parent values or empty (transcript_id will be generated on write)
    if parent_info:
        base = parent_info.model_copy()
    else:
        base = TranscriptInfo(transcript_id="")  # Will be generated on write

    # Overlay explicit info param
    if explicit_info:
        for field_name in TranscriptInfo.model_fields:
            val = getattr(explicit_info, field_name)
            if val is not None:
                setattr(base, field_name, val)

    # Overlay explicit kwargs (highest precedence)
    for key, val in kwargs.items():
        if val is not None and hasattr(base, key):
            setattr(base, key, val)

    return base


def _build_transcript(
    ctx: ObserveContext,
    start_time: float,
    error: Exception | None = None,
) -> Transcript:
    """Build Transcript from context with auto-populated fields.

    Args:
        ctx: The observe context containing info and events.
        start_time: When the observe context started (from time.time()).
        error: Exception that occurred, if any.

    Returns:
        Complete Transcript ready for database insertion.
    """
    # Always generate fresh transcript_id for this leaf (prevents duplication)
    info = ctx.info.model_copy()
    info.transcript_id = str(uuid.uuid4())

    # Auto-populate date
    info.date = datetime.now(timezone.utc).isoformat()

    # Auto-populate total_time
    info.total_time = time.time() - start_time

    # Auto-populate error if exception occurred
    if error is not None:
        info.error = str(error)

    # Extract events from Inspect AI transcript
    events = list(ctx.inspect_transcript.events)

    # Extract data from FINAL ModelEvent (messages, model, config)
    messages: list[ChatMessage] = []
    total_tokens = 0

    for event in reversed(events):
        if isinstance(event, ModelEvent):
            # Found final ModelEvent - extract its messages
            messages.extend(event.input)
            output = event.output
            if isinstance(output, ModelOutput) and output.message:
                messages.append(output.message)

            # Auto-populate model if not explicitly set
            if info.model is None:
                info.model = event.model

            # Auto-populate model_options if not explicitly set
            if info.model_options is None:
                config_dict = event.config.model_dump(exclude_none=True)
                if config_dict:
                    info.model_options = config_dict

            break  # Only use the last ModelEvent

    # Sum tokens from ALL ModelEvents
    for event in events:
        if isinstance(event, ModelEvent):
            output = event.output
            if isinstance(output, ModelOutput) and output.usage:
                total_tokens += output.usage.total_tokens

    # Auto-populate counts
    info.message_count = len(messages)
    info.total_tokens = total_tokens if total_tokens > 0 else None

    return Transcript(
        **info.model_dump(),
        messages=messages,
        events=events,
    )
