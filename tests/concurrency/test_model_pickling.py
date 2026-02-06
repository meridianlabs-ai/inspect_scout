"""Tests that Model objects survive pickling for multiprocess scanning."""

import cloudpickle
from inspect_ai.model import ModelOutput, get_model
from inspect_ai.model._model_config import model_roles_to_model_roles_config
from inspect_scout import llm_scanner


def test_llm_scanner_with_model_instance_is_picklable() -> None:
    """llm_scanner closures must survive cloudpickle roundtrip for multiprocess."""
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
    # This is what DillCallable.__init__ does — must not raise
    pickled = cloudpickle.dumps(scan_fn)
    restored = cloudpickle.loads(pickled)
    assert callable(restored)


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
