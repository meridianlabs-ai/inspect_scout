from typing import Sequence

from inspect_ai.event import Event, SpanBeginEvent, SpanEndEvent
from inspect_ai.log import Transcript

from inspect_scout._util.attachments import resolve_event_attachments


class ItemEvents:
    """Splits one Inspect transcript's events among a loader's items.

    The transcript is initialized once for the whole loader, so a saved
    `transcript()` reference or a task the loader started keeps recording
    into it across yields. Each item's report takes only the events recorded
    since the previous item, led by the begin events of spans still open at
    that point so that every span reference in the slice resolves.
    """

    def __init__(self, transcript: Transcript) -> None:
        self._transcript = transcript
        self._cursor = 0
        self._open_spans: dict[str, SpanBeginEvent] = {}

    def take(self) -> Sequence[Event]:
        """Events since the previous take or skip, with attachments resolved."""
        open_spans = list(self._open_spans.values())
        events = [*open_spans, *self._advance()]
        return resolve_event_attachments(events, self._transcript.attachments)

    def skip(self) -> None:
        """Drop the events since the previous take or skip (an item with no report)."""
        self._advance()

    def _advance(self) -> Sequence[Event]:
        events = self._transcript.history.events_from(self._cursor)
        self._cursor += len(events)
        for event in events:
            if isinstance(event, SpanBeginEvent):
                self._open_spans[event.id] = event
            elif isinstance(event, SpanEndEvent):
                self._open_spans.pop(event.id, None)
        return events
