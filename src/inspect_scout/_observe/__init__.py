"""Observe decorator/context manager for transcript capture.

The `observe` decorator intercepts LLM calls and writes transcripts
to the database, using implicit leaf detection for automatic write triggering.

Supports multiple providers for capturing LLM calls:
- "inspect" (default): Captures Inspect AI model.generate() calls
- "openai": Captures OpenAI SDK calls
- "anthropic": Captures Anthropic SDK calls
- "google": Captures Google GenAI SDK calls
- Custom providers: Implement the ObserveProvider protocol
"""

from ._observe import observe, observe_update
from .context import current_observe_context
from .providers import ObserveEmit, ObserveProvider, ObserveProviderName

__all__ = [
    "observe",
    "observe_update",
    "current_observe_context",
    "ObserveEmit",
    "ObserveProvider",
    "ObserveProviderName",
]
