"""Every `TranscriptInfo` field survives each full-read path.

The read paths rebuild a `Transcript` by copying `TranscriptInfo` fields by
hand, so a newly added field is silently dropped (left at its default) unless
every copy site is updated. The field list here comes from
`TranscriptInfo.model_fields`, so a new field is covered automatically and
fails these tests until each path carries it.
"""

import io
from pathlib import Path
from typing import Any, Callable

import pytest
from inspect_ai.model import ChatMessageUser
from inspect_scout._transcript.database.parquet import ParquetTranscriptsDB
from inspect_scout._transcript.eval_log import EvalLogTranscriptsView
from inspect_scout._transcript.json.load_filtered import load_filtered_transcript
from inspect_scout._transcript.types import (
    Transcript,
    TranscriptContent,
    TranscriptInfo,
)
from pydantic import JsonValue

EVAL_LOG = (
    Path(__file__).parent.parent
    / "recorder"
    / "logs"
    / "2025-11-07T10-59-47-05-00_websearch-addition-problem_LqPDntDnkk4h2fSqQ8i6CE.eval"
)

FIELDS = list(TranscriptInfo.model_fields)

# Read paths may add sample metadata, target and scores to `metadata`, so it
# is checked for containment rather than equality.
METADATA_FIELD = "metadata"

# Builds a non-default value for each annotation used by `TranscriptInfo`,
# from the field's name and position so that values differ between fields and
# a value copied into the wrong field is caught (bool has only one non-default
# value). A field with an annotation missing here raises, so a new field type
# must be added.
_VALUE_BY_ANNOTATION: dict[Any, Callable[[str, int], Any]] = {
    str: lambda name, i: f"{name}-value",
    str | None: lambda name, i: f"{name}-value",
    int | None: lambda name, i: 100 + i,
    float | None: lambda name, i: 100.5 + i,
    bool | None: lambda name, i: True,
    dict[str, Any] | None: lambda name, i: {"field": name, "nested": {"n": i}},
    dict[str, Any]: lambda name, i: {f"{name}_key": f"{name}-value"},
    JsonValue | None: lambda name, i: {"field": name, "points": i},
}


def non_default_fields(exclude: frozenset[str] = frozenset()) -> dict[str, Any]:
    """A distinct non-default value for every `TranscriptInfo` field not in `exclude`."""
    values: dict[str, Any] = {}
    for i, (name, field) in enumerate(TranscriptInfo.model_fields.items()):
        if name in exclude:
            continue
        make_value = _VALUE_BY_ANNOTATION.get(field.annotation)
        if make_value is None:
            raise TypeError(
                f"No non-default test value for TranscriptInfo.{name} "
                f"({field.annotation}); add one to _VALUE_BY_ANNOTATION."
            )
        values[name] = make_value(name, i)
    return values


def assert_info_preserved(expected: TranscriptInfo, actual: Transcript) -> None:
    """Assert every `TranscriptInfo` field of `expected` is on `actual`."""
    for name in FIELDS:
        default = TranscriptInfo.model_fields[name].get_default(
            call_default_factory=True
        )
        assert getattr(expected, name) != default, f"{name} is not set by the test"
        if name == METADATA_FIELD:
            for key, value in expected.metadata.items():
                assert actual.metadata.get(key) == value, f"metadata[{key!r}] lost"
        else:
            assert getattr(actual, name) == getattr(expected, name), f"{name} lost"


ALL_CONTENT = TranscriptContent(messages="all", events="all")
NO_CONTENT = TranscriptContent()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "content",
    [ALL_CONTENT, TranscriptContent(messages="all", events=None, metadata=False)],
    ids=["all_content", "messages_only_no_metadata"],
)
async def test_eval_log_read_preserves_info(content: TranscriptContent) -> None:
    async with EvalLogTranscriptsView(str(EVAL_LOG)) as view:
        indexed = await anext(aiter(view.select()))
        # transcript_id and source_uri locate the sample, so they keep their
        # (already non-default) indexed values.
        info = indexed.model_copy(
            update=non_default_fields(
                exclude=frozenset({"transcript_id", "source_uri"})
            )
        )
        transcript = await view.read(info, content)

    assert_info_preserved(info, transcript)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "sample_json",
    [
        b'{"messages": [], "events": [], "metadata": {"x": 1}}',
        # NaN is rejected by the streaming parser, forcing the json5 fallback.
        b'{"messages": [], "events": [], "metadata": {"x": NaN}}',
    ],
    ids=["streaming", "json5_fallback"],
)
async def test_load_filtered_transcript_preserves_info(sample_json: bytes) -> None:
    info = TranscriptInfo(**non_default_fields())

    transcript = await load_filtered_transcript(
        io.BytesIO(sample_json), info, "all", "all"
    )

    assert_info_preserved(info, transcript)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "content", [ALL_CONTENT, NO_CONTENT], ids=["with_content", "no_content"]
)
async def test_parquet_insert_then_read_preserves_info(
    tmp_path: Path, content: TranscriptContent
) -> None:
    original = Transcript(
        **non_default_fields(), messages=[ChatMessageUser(content="hello")], events=[]
    )
    db = ParquetTranscriptsDB(str(tmp_path))
    await db.connect()
    try:
        await db.insert([original])
        info = await anext(aiter(db.select()))
        transcript = await db.read(info, content)
    finally:
        await db.disconnect()

    assert_info_preserved(original, transcript)
