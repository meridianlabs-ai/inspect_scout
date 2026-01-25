"""Provider for Inspect AI's built-in transcript capture."""

from typing import Any

from inspect_ai.event import Event

from .provider import ObserveEmit


class InspectProvider:
    """Provider for Inspect AI's built-in transcript capture.

    This provider is a no-op - Inspect AI's model.generate() already captures
    via init_transcript(). The emit callback is not used since Inspect handles
    event emission internally.
    """

    def install(self, emit: ObserveEmit) -> None:
        """No-op installation - Inspect AI handles capture internally."""
        # No-op - Inspect AI's model.generate() already captures via init_transcript()
        # The emit callback is not used since Inspect handles event emission internally
        pass

    async def build_event(self, data: dict[str, Any]) -> Event:
        """Never called since install() doesn't use emit."""
        raise NotImplementedError("InspectProvider does not emit raw data")
