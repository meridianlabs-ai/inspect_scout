"""End-to-end regression test for issue #537.

A scanner whose closure captures an inspect_ai ``Model`` must survive a real
spawn multiprocessing scan. ``max_processes >= 2`` forces the spawn path, which
serializes the scanner closure via ``DillCallable`` -> ``scout_dumps``. Because
the closure captures a ``Model`` directly, this exercises the ``ScoutPickler``
reducer end to end: the ``Model`` is reduced to a ``ModelConfig`` on the parent
side and reconstructed via ``get_model()`` in each worker.

The scanner derives its ``Result`` from the captured ``Model`` without any
network call, so what's under test is the serialization roundtrip across the
process boundary (not model generation).

NOTE: this module intentionally does NOT use ``from __future__ import
annotations``. Scout's implicit-loader detection compares the scanner's first
parameter annotation against the ``Transcript`` class by identity; under PEP 563
that annotation would be the string ``"Transcript"`` and detection would fail.
"""

import asyncio
from pathlib import Path

from inspect_ai.model import get_model
from inspect_ai.model._chat_message import ChatMessageUser
from inspect_ai.model._model import Model
from inspect_scout import Result, Scanner, scan, scanner, transcripts_db
from inspect_scout._scanresults import scan_results_df
from inspect_scout._transcript.factory import transcripts_from
from inspect_scout._transcript.types import Transcript


def _model_capture_scanner_factory(captured_model: Model) -> Scanner[Transcript]:
    @scanner(name="model_capture_scanner", messages="all")
    def factory() -> Scanner[Transcript]:
        async def scan_transcript(transcript: Transcript) -> Result:
            # Uses the closure-captured Model without a network call; reaching
            # here at all proves the closure (and its Model) survived spawn.
            return Result(
                value=str(captured_model.name),
                explanation=f"api={captured_model.api.__class__.__name__}",
            )

        return scan_transcript

    return factory()


def test_model_capturing_closure_survives_multiprocess_scan(tmp_path: Path) -> None:
    """A scanner closure that captures a Model runs across spawned workers."""
    captured_model = get_model("mockllm/model")

    db_path = tmp_path / "db"
    scans_path = tmp_path / "scans"
    db_path.mkdir()
    scans_path.mkdir()

    async def insert() -> None:
        transcripts = [
            Transcript(
                transcript_id=f"t-{i:03d}",
                source_type="test",
                source_id="s",
                source_uri=f"test://{i}",
                metadata={"index": i},
                messages=[ChatMessageUser(content=f"msg {i}")],
                events=[],
            )
            for i in range(6)
        ]
        async with transcripts_db(str(db_path)) as db:
            await db.insert(transcripts)

    asyncio.run(insert())

    status = scan(
        scanners=[_model_capture_scanner_factory(captured_model)],
        transcripts=transcripts_from(str(db_path)),
        scans=str(scans_path),
        max_processes=2,  # forces spawn multiprocessing -> DillCallable/scout_dumps
        display="none",
    )

    assert status.complete
    assert status.location is not None

    df = scan_results_df(status.location, scanner="model_capture_scanner").scanners[
        "model_capture_scanner"
    ]
    assert len(df) == 6
    # The Model was faithfully reconstructed in each worker.
    assert df["value"].tolist() == ["model"] * 6
    assert all(e == "api=MockLLM" for e in df["explanation"].tolist())
