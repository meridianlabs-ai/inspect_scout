"""Tests that scanner closures survive pickling for multiprocess scanning.

The multiprocess pipeline serializes scanner closures with cloudpickle and sends
them to spawned worker processes via DillCallable.  These tests verify that
Model objects, Pydantic grading classes, and closures that capture them survive
the cloudpickle roundtrip intact.
"""

from __future__ import annotations

import base64
import copyreg
import json
import subprocess
import sys
from pathlib import Path

import cloudpickle  # type: ignore[import-untyped]
import inspect_scout._concurrency._mp_common  # noqa: F401 — registers copyreg reducer
from inspect_ai.model import ModelOutput, get_model
from inspect_ai.model._model import Model
from inspect_ai.model._model_config import model_roles_to_model_roles_config
from inspect_scout import llm_scanner

# Scanner file whose grading class contains a ModelEvent field.  Loaded via
# load_module (exactly as inspect_ai loads user-authored scanner files).
_SCANNER_WITH_MODEL_EVENT = (
    Path(__file__).resolve().parent / "scanner_with_model_event.py"
)


# ---------------------------------------------------------------------------
# copyreg reducer for Model
# ---------------------------------------------------------------------------


def test_copyreg_reducer_is_registered() -> None:
    """Importing _mp_common registers a copyreg reducer for Model."""
    assert Model in copyreg.dispatch_table


def test_model_survives_cloudpickle_roundtrip_in_subprocess() -> None:
    """Model must survive cloudpickle serialization in a real subprocess.

    Same-process cloudpickle.loads() can return the original object via identity
    shortcuts, so we must verify in a subprocess to be a valid test.
    """
    model = get_model("mockllm/model")
    pickled = cloudpickle.dumps(model)

    # Verify in subprocess
    model_b64 = base64.b64encode(pickled).decode()
    syspath_json = json.dumps(sys.path)
    script = (
        "import sys, base64, json, cloudpickle\n"
        f"sys.path = json.loads({syspath_json!r})\n"
        f"pickled = base64.b64decode({model_b64!r})\n"
        "model = cloudpickle.loads(pickled)\n"
        "result = json.dumps({'name': str(model.name), 'api_name': model.api.__class__.__name__})\n"
        "print(result)\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        timeout=15,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Subprocess failed (rc={result.returncode}):\n{result.stderr}"
        )
    info = json.loads(result.stdout.strip())
    # model.name returns the short name (without provider prefix)
    assert info["name"] == "model"


# ---------------------------------------------------------------------------
# PR #260: Model objects in scanner closures
# ---------------------------------------------------------------------------


def test_llm_scanner_with_model_instance_is_picklable() -> None:
    """llm_scanner closures must survive cloudpickle roundtrip in a subprocess.

    cloudpickle.loads() in the same process returns the original class object
    (identity-preserving), so the test must deserialize in a fresh subprocess
    to validate that the closure truly survives the roundtrip.
    """
    model = get_model(
        "mockllm/model",
        custom_outputs=[
            ModelOutput.from_content("mockllm/model", content="ANSWER: 0.5")
        ],
    )
    scan_fn = llm_scanner(
        question="Is this suspicious?",
        answer="numeric",
        model=model,
        name="test_scanner",
    )
    # This is what DillCallable.__init__ does
    pickled = cloudpickle.dumps(scan_fn)
    # Verify in a subprocess where cloudpickle can't use identity shortcuts
    assert _unpickle_callable_in_subprocess(pickled)


def test_model_roles_config_is_picklable() -> None:
    """model_roles converted to ModelConfig must survive pickling for IPCContext."""
    model = get_model(
        "mockllm/model",
        custom_outputs=[ModelOutput.from_content("mockllm/model", content="hello")],
    )
    roles = {"scanner": model}
    roles_config = model_roles_to_model_roles_config(roles)
    # This is what happens when IPCContext crosses process boundary
    pickled = cloudpickle.dumps(roles_config)
    restored = cloudpickle.loads(pickled)
    assert restored is not None
    assert "scanner" in restored


# ---------------------------------------------------------------------------
# Subprocess helper
# ---------------------------------------------------------------------------


def _unpickle_callable_in_subprocess(pickled: bytes) -> bool:
    """Deserialize a cloudpickled callable in a subprocess and verify it works.

    cloudpickle.loads() in the same process returns the original object
    (identity-preserving), so this must run in a fresh process to be a
    valid test.
    """
    fn_b64 = base64.b64encode(pickled).decode()

    # Pass parent sys.path so the subprocess can resolve imports
    # (mirrors how Scout's multiprocess workers inherit sys.path).
    syspath_json = json.dumps(sys.path)
    script = (
        "import sys, base64, json, cloudpickle\n"
        f"sys.path = json.loads({syspath_json!r})\n"
        f"pickled = base64.b64decode({fn_b64!r})\n"
        "fn = cloudpickle.loads(pickled)\n"
        "assert callable(fn), 'deserialized object is not callable'\n"
        "print('ok')\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        timeout=15,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Subprocess failed (rc={result.returncode}):\n{result.stderr}"
        )
    return result.stdout.strip() == "ok"


# ---------------------------------------------------------------------------
# Pydantic grading class with ModelEvent — cloudpickle + load_module bug
#
# When a grading class references ModelEvent (which uses @model_validator
# and self-referential types internally), cloudpickle's by-value
# serialization breaks Pydantic's core schema.  model_dump() returns {}
# in the subprocess.  The bug only manifests in a real subprocess because
# cloudpickle.loads() in the same process returns the original class object.
# ---------------------------------------------------------------------------

# NOTE: comment this back in once we've applied the Insepct fix

# def test_grading_class_with_model_event_survives_subprocess() -> None:
#     """Grading class containing ModelEvent must work after cloudpickle in subprocess.

#     ModelEvent uses @model_validator(mode="after") on ModelOutput and
#     @model_validator(mode="wrap") on ChatMessageBase.  When load_module sets
#     __module__ to a file path, cloudpickle falls back to by-value serialization
#     which breaks these patterns — model_dump() silently returns {}.
#     """
#     module = load_module(_SCANNER_WITH_MODEL_EVENT)
#     grading_cls = module.GradingWithEvent

#     data = {"value": 0.8, "label": "good", "source_event": None}
#     expected = {"score": 0.8, "event_summary": "good", "source_event": None}

#     # Works in the current process
#     assert grading_cls.model_validate(data).model_dump() == expected

#     # Must also work in a subprocess (currently broken: returns {})
#     pickled = cloudpickle.dumps(grading_cls)
#     result = _model_dump_in_subprocess(pickled, data)
#     assert result == expected


# # ---------------------------------------------------------------------------
# # Subprocess helper
# # ---------------------------------------------------------------------------


# def _model_dump_in_subprocess(
#     pickled_cls: bytes,
#     data: dict[str, Any],
#     *,
#     rebuild: bool = False,
# ) -> dict[str, Any]:
#     """Deserialize a cloudpickled class in a subprocess and return model_dump().

#     cloudpickle.loads() in the same process returns the original class object
#     (identity-preserving), so the bug only manifests in a fresh process.
#     """
#     cls_b64 = base64.b64encode(pickled_cls).decode()
#     data_json = json.dumps(data)
#     rebuild_line = "cls.model_rebuild(force=True)" if rebuild else ""

#     # Pass parent sys.path so the subprocess can import modules by their
#     # dotted names (mirrors how Scout's multiprocess workers inherit sys.path).
#     syspath_json = json.dumps(sys.path)
#     script = (
#         "import sys, base64, json, cloudpickle\n"
#         f"sys.path = json.loads({syspath_json!r})\n"
#         f"pickled = base64.b64decode({cls_b64!r})\n"
#         "cls = cloudpickle.loads(pickled)\n"
#         f"{rebuild_line}\n"
#         f"inst = cls.model_validate(json.loads({data_json!r}))\n"
#         "print(json.dumps(inst.model_dump()))\n"
#     )
#     result = subprocess.run(
#         [sys.executable, "-c", script],
#         capture_output=True,
#         text=True,
#         timeout=15,
#     )
#     if result.returncode != 0:
#         raise RuntimeError(
#             f"Subprocess failed (rc={result.returncode}):\n{result.stderr}"
#         )
#     return json.loads(result.stdout.strip())  # type: ignore[no-any-return]
