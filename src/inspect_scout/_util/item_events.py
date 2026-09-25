from typing import NamedTuple, Sequence

from inspect_ai.event import Event, SpanBeginEvent, SpanEndEvent
from inspect_ai.log import Transcript

from inspect_scout._util.attachments import resolve_event_attachments


class _SpanBegin(NamedTuple):
    position: int
    """Index of the event in the transcript's history."""

    event: SpanBeginEvent


class ItemEvents:
    """Splits one Inspect transcript's events among a loader's items.

    The transcript is initialized once for the whole loader, so a saved
    `transcript()` reference or a task the loader started keeps recording
    into it across yields. Each item's report takes only the events recorded
    since the previous item, led by the begin events of the spans those
    events reference (and their ancestors) that began earlier, so that every
    span reference in the slice resolves, even to a span that has ended.
    """

    def __init__(self, transcript: Transcript) -> None:
        self._transcript = transcript
        self._cursor = 0
        self._span_begins: dict[str, _SpanBegin] = {}

    def take(self) -> Sequence[Event]:
        """Events since the previous take or skip, with attachments resolved."""
        events = self._advance()
        events = [*self._earlier_ancestry(events), *events]
        return resolve_event_attachments(events, self._transcript.attachments)

    def skip(self) -> None:
        """Drop the events since the previous take or skip (an item with no report)."""
        self._advance()

    def _advance(self) -> Sequence[Event]:
        events = self._transcript.history.events_from(self._cursor)
        for offset, event in enumerate(events):
            if isinstance(event, SpanBeginEvent):
                self._span_begins[event.id] = _SpanBegin(self._cursor + offset, event)
        self._cursor += len(events)
        return events

    def _earlier_ancestry(self, events: Sequence[Event]) -> list[SpanBeginEvent]:
        """Earlier begin events of the spans `events` reference, in history order."""
        begun = {event.id for event in events if isinstance(event, SpanBeginEvent)}
        pending: list[str | None] = []
        for event in events:
            pending.append(event.span_id)
            if isinstance(event, SpanBeginEvent):
                pending.append(event.parent_id)
            elif isinstance(event, SpanEndEvent):
                pending.append(event.id)
        found: dict[str, _SpanBegin] = {}
        while pending:
            span_id = pending.pop()
            if span_id is None or span_id in begun or span_id in found:
                continue
            begin = self._span_begins.get(span_id)
            if begin is None:
                continue
            found[span_id] = begin
            pending.append(begin.event.parent_id)
        return [
            begin.event for begin in sorted(found.values(), key=lambda b: b.position)
        ]
