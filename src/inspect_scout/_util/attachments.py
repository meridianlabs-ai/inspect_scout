from typing import Mapping, Sequence

from inspect_ai.event import Event
from inspect_ai.log._condense import ATTACHMENT_PROTOCOL, WalkContext, walk_events


def resolve_event_attachments(
    events: Sequence[Event], attachments: Mapping[str, str]
) -> Sequence[Event]:
    def content_fn(text: str) -> str:
        if text.startswith(ATTACHMENT_PROTOCOL):
            return attachments.get(text.replace(ATTACHMENT_PROTOCOL, "", 1), text)
        else:
            return text

    context = WalkContext(message_cache={}, only_core=False)

    return walk_events(list(events), content_fn, context)
