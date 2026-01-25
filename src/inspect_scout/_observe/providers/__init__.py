"""Providers for LLM call capture.

This module provides the infrastructure for capturing LLM calls made through
various SDK providers (OpenAI, Anthropic, Google) in addition to Inspect AI's
built-in model API.
"""

from .provider import (
    ObserveEmit,
    ObserveProvider,
    ObserveProviderName,
    get_provider_instance,
    install_providers,
)

__all__ = [
    # Protocol and types (public API for custom providers)
    "ObserveEmit",
    "ObserveProvider",
    "ObserveProviderName",
    # Internal functions (used by _observe.py)
    "get_provider_instance",
    "install_providers",
]
