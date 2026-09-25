from typing import Sequence

from inspect_ai.event import Event
from inspect_ai.log import Transcript
from inspect_ai.log._condense import ATTACHMENT_PROTOCOL, WalkContext, walk_events


def resolve_event_attachments(transcript: Transcript) -> Sequence[Event]:
    def content_fn(text: str) -> str:
        if text.startswith(ATTACHMENT_PROTOCOL):
            return transcript.attachments.get(
                text.replace(ATTACHMENT_PROTOCOL, "", 1), text
            )
        else:
            return text

    context = WalkContext(message_cache={}, only_core=False)

    return walk_events(list(transcript.events), content_fn, context)
