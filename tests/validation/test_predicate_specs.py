"""Tests for portable validation predicate specifications."""

from __future__ import annotations

import base64
import json
import pickle
from collections.abc import AsyncIterator
from pathlib import Path
from typing import cast

import pytest
from fastapi.testclient import TestClient
from inspect_ai._util.error import PrerequisiteError
from inspect_ai._util.module import load_module
from inspect_ai._util.registry import _registry, registry_key
from inspect_scout import (
    PredicateFn,
    Result,
    ValidationCase,
    ValidationPredicate,
    ValidationSet,
    scan,
    scan_resume,
    validation_predicate,
)
from inspect_scout._recorder.file import FileRecorder
from inspect_scout._recorder.summary import Summary
from inspect_scout._scanspec import ScanSpec
from inspect_scout._transcript.factory import transcripts_from
from inspect_scout._validation.spec import (
    validation_set_to_spec,
    validation_sets_from_specs,
)
from inspect_scout._validation.types import (
    RegisteredPredicateSpec,
    UnavailablePredicateSpec,
    ValidationSetSpec,
)
from inspect_scout._validation.validate import validate
from inspect_scout._view._api_v2 import v2_api_app
from pydantic import JsonValue, ValidationError

LOGS_DIR = Path(__file__).parent.parent / "recorder" / "logs"


@validation_predicate
def within_range(distance: float = 10) -> ValidationPredicate:
    """Create a numeric range predicate for registry round-trip tests."""

    async def check(result: Result, target: JsonValue) -> bool:
        if not isinstance(result.value, (int, float)):
            return False
        if not isinstance(target, (int, float)):
            return False
        return abs(result.value - target) <= distance

    return check


def test_registered_predicate_serializes_as_data() -> None:
    validation = ValidationSet(cases=[], predicate=within_range(distance=5))

    spec = validation_set_to_spec(validation)

    assert isinstance(spec.predicate, RegisteredPredicateSpec)
    assert spec.predicate.name == "within_range"
    assert spec.predicate.args == {"distance": 5}
    assert spec.predicate.file == Path(__file__).relative_to(Path.cwd()).as_posix()
    serialized = spec.model_dump_json()
    assert '"kind":"registered"' in serialized
    assert "gASV" not in serialized


@pytest.mark.parametrize("distance", [float("nan"), float("inf"), float("-inf")])
def test_registered_predicate_rejects_non_finite_args(distance: float) -> None:
    validation = ValidationSet(cases=[], predicate=within_range(distance=distance))

    with pytest.raises(ValidationError, match="finite number"):
        validation_set_to_spec(validation)


def test_registered_predicate_rejects_async_generator() -> None:
    @validation_predicate(name="async_generator_predicate")
    def async_generator_predicate() -> ValidationPredicate:
        async def check(result: Result, target: JsonValue) -> AsyncIterator[bool]:
            yield result.value == target

        return cast(ValidationPredicate, check)

    with pytest.raises(TypeError, match="must be an async callable"):
        async_generator_predicate()


@pytest.mark.asyncio
async def test_registered_predicate_recreates_from_registry() -> None:
    validation = ValidationSet(cases=[], predicate=within_range(distance=5))
    spec = validation_set_to_spec(validation)
    assert isinstance(spec.predicate, RegisteredPredicateSpec)

    # The current module has already registered the factory, so no source load
    # is required for this focused registry round-trip.
    spec.predicate.file = None
    restored = validation_sets_from_specs({"scanner": spec})

    assert restored is not None
    assert await validate(restored["scanner"], Result(value=12), 10) is True
    assert await validate(restored["scanner"], Result(value=20), 10) is False


@pytest.mark.asyncio
async def test_registered_predicate_recreates_from_source_file(
    tmp_path: Path,
) -> None:
    predicate_file = tmp_path / "predicate.py"
    predicate_file.write_text(
        "\n".join(
            [
                "from pydantic import JsonValue",
                "from inspect_scout import (",
                "    Result,",
                "    ValidationPredicate,",
                "    validation_predicate,",
                ")",
                "",
                "@validation_predicate(name='temporary/starts_with')",
                "def starts_with(prefix: str) -> ValidationPredicate:",
                "    async def check(result: Result, target: JsonValue) -> bool:",
                "        return str(result.value).startswith(prefix + str(target))",
                "    return check",
            ]
        )
    )
    spec = ValidationSetSpec(
        cases=[],
        predicate=RegisteredPredicateSpec(
            name="temporary/starts_with",
            args={"prefix": "safe-"},
            file=predicate_file.as_posix(),
        ),
    )

    restored = validation_sets_from_specs({"scanner": spec})

    assert restored is not None
    assert (
        await validate(
            restored["scanner"],
            Result(value="safe-target"),
            "target",
        )
        is True
    )


@pytest.mark.asyncio
async def test_anonymous_predicate_requires_override() -> None:
    async def normalized_equal(result: Result, target: JsonValue) -> bool:
        return str(result.value).strip().lower() == str(target).strip().lower()

    spec = validation_set_to_spec(ValidationSet(cases=[], predicate=normalized_equal))

    assert spec.predicate == UnavailablePredicateSpec(
        display_name="normalized_equal",
        reason="anonymous",
    )
    with pytest.raises(PrerequisiteError, match="predicate_overrides"):
        validation_sets_from_specs({"scanner": spec})

    restored = validation_sets_from_specs(
        {"scanner": spec},
        {"scanner": normalized_equal},
    )

    assert restored is not None
    assert await validate(restored["scanner"], Result(value=" Yes "), "yes") is True


def test_override_for_builtin_predicate_is_rejected() -> None:
    async def custom(result: Result, target: JsonValue) -> bool:
        return result.value == target

    with pytest.raises(PrerequisiteError, match="do not match"):
        validation_sets_from_specs(
            {"scanner": ValidationSetSpec(cases=[], predicate="eq")},
            {"scanner": custom},
        )


def test_builtin_name_override_for_custom_predicate_is_rejected() -> None:
    with pytest.raises(PrerequisiteError, match="must be async callables"):
        validation_sets_from_specs(
            {
                "scanner": ValidationSetSpec(
                    cases=[],
                    predicate=UnavailablePredicateSpec(reason="anonymous"),
                )
            },
            {"scanner": "eq"},  # type: ignore[dict-item]
        )


def test_async_generator_override_is_rejected() -> None:
    async def async_generator_override(
        result: Result, target: JsonValue
    ) -> AsyncIterator[bool]:
        yield result.value == target

    with pytest.raises(PrerequisiteError, match="must be async callables"):
        validation_sets_from_specs(
            {
                "scanner": ValidationSetSpec(
                    cases=[],
                    predicate=UnavailablePredicateSpec(reason="anonymous"),
                )
            },
            {"scanner": cast(PredicateFn, async_generator_override)},
        )


def test_missing_override_fails_before_registered_source_load(
    tmp_path: Path,
) -> None:
    import_marker = tmp_path / "imported.txt"
    predicate_file = tmp_path / "predicate.py"
    predicate_file.write_text(
        "\n".join(
            [
                "from pathlib import Path",
                f"Path({str(import_marker)!r}).write_text('IMPORTED')",
            ]
        )
    )
    specs = {
        "anonymous": ValidationSetSpec(
            cases=[],
            predicate=UnavailablePredicateSpec(reason="anonymous"),
        ),
        "registered": ValidationSetSpec(
            cases=[],
            predicate=RegisteredPredicateSpec(
                name="missing/predicate",
                file=predicate_file.as_posix(),
            ),
        ),
    }

    with pytest.raises(PrerequisiteError, match="anonymous"):
        validation_sets_from_specs(specs)

    assert not import_marker.exists()


def test_legacy_pickle_payload_is_never_deserialized(tmp_path: Path) -> None:
    marker = tmp_path / "marker.txt"
    expression = (
        f"__import__('pathlib').Path({str(marker)!r})"
        ".write_text('LEGACY_PREDICATE_EXECUTED')"
    )

    class MarkerPayload:
        def __reduce__(self) -> tuple[object, tuple[str]]:
            return eval, (expression,)

    payload = base64.b64encode(pickle.dumps(MarkerPayload())).decode("ascii")
    spec = ScanSpec.model_validate(
        {
            "scan_name": "malicious",
            "scanners": {},
            "validation": {
                "scanner": {
                    "cases": [ValidationCase(id="id-1", target=True).model_dump()],
                    "predicate": payload,
                }
            },
        }
    )

    assert not marker.exists()
    assert spec.validation is not None
    predicate = spec.validation["scanner"].predicate
    assert predicate == UnavailablePredicateSpec(reason="legacy")
    assert payload not in spec.model_dump_json()


def test_malformed_legacy_predicate_is_redacted_from_validation_errors() -> None:
    payload = "STARTLEAK_" + ("A" * 100) + "_ENDLEAK"

    with pytest.raises(ValidationError) as exc_info:
        ScanSpec.model_validate(
            {
                "scan_name": "malformed",
                "scanners": {},
                "validation": {
                    "scanner": {
                        "predicate": payload,
                    }
                },
            }
        )

    assert "STARTLEAK" not in str(exc_info.value)
    assert "ENDLEAK" not in str(exc_info.value)
    assert payload not in repr(exc_info.value.errors())


@pytest.mark.asyncio
async def test_file_recorder_status_treats_legacy_predicate_as_data(
    tmp_path: Path,
) -> None:
    marker = tmp_path / "marker.txt"
    expression = (
        f"__import__('pathlib').Path({str(marker)!r})"
        ".write_text('LEGACY_STATUS_EXECUTED')"
    )

    class MarkerPayload:
        def __reduce__(self) -> tuple[object, tuple[str]]:
            return eval, (expression,)

    payload = base64.b64encode(pickle.dumps(MarkerPayload())).decode("ascii")
    scan_dir = tmp_path / "scan_id=legacy"
    scan_dir.mkdir()
    (scan_dir / "_scan.json").write_text(
        json.dumps(
            {
                "scan_id": "legacy",
                "scan_name": "legacy",
                "scanners": {"scanner": {"name": "scanner"}},
                "validation": {
                    "scanner": {
                        "cases": [{"id": "id-1", "target": True}],
                        "predicate": payload,
                    }
                },
            }
        )
    )
    (scan_dir / "_summary.json").write_text(
        Summary(scanners=["scanner"]).model_dump_json()
    )

    status = await FileRecorder.status(scan_dir.as_posix())

    assert not marker.exists()
    assert status.spec.validation is not None
    assert status.spec.validation["scanner"].predicate == UnavailablePredicateSpec(
        reason="legacy"
    )


def test_scan_list_api_treats_legacy_predicate_as_data(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    marker = tmp_path / "marker.txt"
    expression = (
        f"__import__('pathlib').Path({str(marker)!r})"
        ".write_text('LEGACY_LIST_EXECUTED')"
    )

    class MarkerPayload:
        def __reduce__(self) -> tuple[object, tuple[str]]:
            return eval, (expression,)

    payload = base64.b64encode(pickle.dumps(MarkerPayload())).decode("ascii")
    scans_dir = tmp_path / "scans"
    scan_dir = scans_dir / "scan_id=legacy"
    scan_dir.mkdir(parents=True)
    (scan_dir / "_scan.json").write_text(
        json.dumps(
            {
                "scan_id": "legacy",
                "scan_name": "legacy",
                "scanners": {"scanner": {"name": "scanner"}},
                "validation": {
                    "scanner": {
                        "cases": [{"id": "id-1", "target": True}],
                        "predicate": payload,
                    }
                },
            }
        )
    )
    (scan_dir / "_summary.json").write_text(
        Summary(scanners=["scanner"]).model_dump_json()
    )
    cache = tmp_path / "cache"
    monkeypatch.setattr(
        "inspect_scout._scanjobs.cache_path.scout_cache_dir",
        lambda subdir=None: cache / subdir if subdir else cache,
    )
    encoded = (
        base64.urlsafe_b64encode(scans_dir.as_posix().encode()).decode().rstrip("=")
    )

    with TestClient(v2_api_app()) as client:
        response = client.post(f"/scans/{encoded}", json={})

    assert response.status_code == 200
    assert [item["scan_id"] for item in response.json()["items"]] == ["legacy"]
    assert not marker.exists()


def test_registered_predicate_resumes_from_recorded_source(tmp_path: Path) -> None:
    gate = tmp_path / "gate.txt"
    loads = tmp_path / "loads.txt"
    source = tmp_path / "registered_resume.py"
    source.write_text(
        "\n".join(
            [
                "from pathlib import Path",
                "from pydantic import JsonValue",
                "from inspect_scout import (",
                "    Result,",
                "    Scanner,",
                "    Transcript,",
                "    ValidationPredicate,",
                "    scanner,",
                "    validation_predicate,",
                ")",
                f"GATE = Path({str(gate)!r})",
                f"LOADS = Path({str(loads)!r})",
                "LOAD_COUNT = int(LOADS.read_text()) + 1 if LOADS.exists() else 1",
                "LOADS.write_text(str(LOAD_COUNT))",
                "",
                "@scanner(name='resume_scanner', messages='all')",
                "def resume_scanner() -> Scanner[Transcript]:",
                "    async def scan_transcript(transcript: Transcript) -> Result:",
                "        if not GATE.exists():",
                "            GATE.write_text('ready')",
                "            raise RuntimeError('intentional first-run failure')",
                "        return Result(value=True)",
                "    return scan_transcript",
                "",
                "@validation_predicate(name='resume_predicate')",
                "def resume_predicate() -> ValidationPredicate:",
                "    async def check(result: Result, target: JsonValue) -> bool:",
                "        return result.value == target",
                "    return check",
            ]
        )
    )
    module = load_module(source)
    assert loads.read_text() == "1"
    validation = ValidationSet(cases=[], predicate=module.resume_predicate())
    first = scan(
        scanners=[module.resume_scanner()],
        transcripts=transcripts_from(LOGS_DIR),
        validation=validation,
        scans=tmp_path.as_posix(),
        limit=1,
        max_processes=1,
        display="none",
    )
    assert first.complete is False

    # Prove resume can recreate the predicate from the recorded source rather
    # than relying on the original in-memory registry entry.
    _registry.pop(registry_key("validation_predicate", "resume_predicate"))

    resumed = scan_resume(
        first.location,
        display="none",
    )

    assert resumed.complete is True
    assert loads.read_text() == "2"
