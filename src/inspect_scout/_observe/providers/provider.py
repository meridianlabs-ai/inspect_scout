"""Base provider infrastructure for LLM call capture."""

from typing import (
    Any,
    Callable,
    Literal,
    Protocol,
    Sequence,
    runtime_checkable,
)

from inspect_ai.event import Event

# Valid built-in provider names
ObserveProviderName = Literal["inspect", "openai", "anthropic", "google"]

# Callback type - provider calls this with raw captured data (always sync)
ObserveEmit = Callable[[dict[str, Any]], None]
"""Sync function to emit raw captured data. Called by provider wrappers."""


@runtime_checkable
class ObserveProvider(Protocol):
    """Protocol for LLM capture providers."""

    def install(self, emit: ObserveEmit) -> None:
        """Install hooks/patches for capturing LLM calls.

        Called once per provider class. Implementations should be idempotent.

        Args:
            emit: Sync callback to emit raw captured data. Call with a dict
                  containing request/response data. Framework handles context
                  checking - emit() is a no-op if not inside an observe context.
                  The dict structure is provider-defined and passed to build_event().
        """
        ...

    async def build_event(self, data: dict[str, Any]) -> Event:
        """Convert raw captured data to an Inspect Event.

        Called by the framework at observe exit for each captured item.
        This is where async conversion (using Inspect AI converters) happens.

        Args:
            data: The dict passed to emit() during capture.

        Returns:
            An Inspect Event (typically ModelEvent).
        """
        ...


# Registry of installed providers - tracked by class name
_installed_providers: set[str] = set()

# Registry of provider instances by class name (for build_event)
_provider_instances: dict[str, ObserveProvider] = {}


def _get_provider_key(provider: str | ObserveProvider) -> str:
    """Get unique key for a provider (class name for instances, string for names)."""
    if isinstance(provider, str):
        return provider
    return provider.__class__.__name__


def get_provider_instance(key: str) -> ObserveProvider | None:
    """Get provider instance by key."""
    return _provider_instances.get(key)


def create_emit_callback(provider: ObserveProvider) -> ObserveEmit:
    """Create emit callback for a provider (context-checked, queues data)."""
    provider_key = _get_provider_key(provider)

    def emit(data: dict[str, Any]) -> None:
        from ..context import current_observe_context

        ctx = current_observe_context()
        if ctx is not None:
            ctx.pending_captures.append((data, provider_key))

    return emit


def get_provider(
    name: str,
) -> ObserveProvider:
    """Get a provider instance by name.

    Args:
        name: Provider name ('inspect', 'openai', 'anthropic', 'google').

    Returns:
        Provider instance.

    Raises:
        ValueError: If provider name is not recognized.
    """
    if name == "inspect":
        from ._inspect import InspectProvider

        return InspectProvider()
    elif name == "openai":
        from .openai import OpenAIProvider

        return OpenAIProvider()
    elif name == "anthropic":
        from .anthropic import AnthropicProvider

        return AnthropicProvider()
    elif name == "google":
        from .google import GoogleProvider

        return GoogleProvider()
    else:
        raise ValueError(
            f"Unknown provider: {name}. "
            f"Valid providers: 'inspect', 'openai', 'anthropic', 'google'"
        )


def install_providers(
    providers: str | ObserveProvider | Sequence[str | ObserveProvider] | None,
) -> None:
    """Install specified providers (idempotent, tracked by class name).

    Args:
        providers: Provider name(s), instance(s), or sequence of either.
    """
    if providers is None:
        return

    # Normalize to sequence
    if isinstance(providers, (str, ObserveProvider)):
        provider_list: Sequence[str | ObserveProvider] = [providers]
    else:
        provider_list = providers

    for provider in provider_list:
        # Resolve string to provider instance first
        if isinstance(provider, str):
            provider = get_provider(provider)

        # Get key from the resolved provider instance
        key = _get_provider_key(provider)
        if key in _installed_providers:
            continue  # Already installed

        # Store provider instance for build_event
        _provider_instances[key] = provider

        # Create emit callback bound to this provider
        emit = create_emit_callback(provider)
        provider.install(emit)
        _installed_providers.add(key)


def reset_providers() -> None:
    """Reset provider state (for testing only)."""
    global _installed_providers, _provider_instances
    _installed_providers = set()
    _provider_instances = {}
