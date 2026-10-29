"""The streaming handle's metadata merge must not strand unread JSON keys.

``TranscriptHandle._build_transcript`` merges the index row's metadata with the
values the stream parse recovered. That merge is the sibling of the one in
``json/load_filtered.py``; both stranded every :class:`LazyJSONDict` key nobody
had read as its raw JSON string (issue #644). Nothing in the suite reached this
call site, so it is exercised directly here.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from inspect_scout._transcript.handle import _merge_unthinned
from inspect_scout._transcript.json.spool import BlobSpool, ByteSpool, ItemSpool
from inspect_scout._transcript.json.stream_parse import StreamParseResult
from inspect_scout._transcript.util import LazyJSONDict


def _index_metadata() -> LazyJSONDict:
    """Mirrors what ``eval_log.py`` attaches: JSON columns still unparsed."""
    return LazyJSONDict(
        {"eval_metadata": '{"run": "abc"}', "task_args": "{}"},
        json_keys=["eval_metadata", "task_args"],
    )


def _result(
    tmp_path: Path,
    target: str | list[str] | None = None,
    scores: dict[str, Any] | None = None,
) -> StreamParseResult:
    return StreamParseResult(
        ItemSpool(tmp_path),
        ItemSpool(tmp_path),
        BlobSpool(tmp_path),
        ByteSpool(tmp_path),
        tmp_path,
        target=target,
        scores=scores or {},
    )


def test_merge_keeps_index_json_parseable_when_overrides_exist(
    tmp_path: Path,
) -> None:
    """A recovered target is an override, which used to force a plain-dict copy."""
    merged = _merge_unthinned(
        _index_metadata(), _result(tmp_path, target="summary-target")
    )
    assert merged["eval_metadata"] == {"run": "abc"}
    assert merged["task_args"] == {}
    assert merged["target"] == "summary-target"


def test_merge_returns_base_when_there_is_nothing_to_override(
    tmp_path: Path,
) -> None:
    base = _index_metadata()
    assert _merge_unthinned(base, _result(tmp_path)) is base


def test_merge_does_not_mutate_the_index_row(tmp_path: Path) -> None:
    base = _index_metadata()
    _merge_unthinned(base, _result(tmp_path, target="t"))
    assert "target" not in base
