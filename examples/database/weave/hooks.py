import os
from contextlib import _GeneratorContextManager

import weave
from inspect_ai.hooks import (
    Hooks,
    RunEnd,
    RunStart,
    SampleEnd,
    SampleStart,
    TaskEnd,
    TaskStart,
    hooks,
)
from inspect_ai.log import EvalSpec
from pydantic_core import to_jsonable_python
from weave.trace.call import Call
from weave.trace.weave_client import WeaveClient


@hooks(name="weave_hooks", description="Weights & Biases Weave")
class WeaveHooks(Hooks):
    def __init__(self) -> None:
        self._client: WeaveClient | None = None
        self._evals: dict[str, EvalSpec] = {}
        self._threads: dict[
            str, tuple[_GeneratorContextManager[weave.ThreadContext, None, None], Call]
        ] = {}

    def enabled(self) -> bool:
        return (
            os.getenv("WANDB_PROJECT_ID", None) is not None
            and os.getenv("WANDB_API_KEY", None) is not None
        )

    async def on_run_start(self, data: RunStart) -> None:
        self._client = weave.init(project_name=os.getenv("WANDB_PROJECT_ID", ""))

    async def on_run_end(self, data: RunEnd) -> None:
        assert self._client
        self._client.finish()
        self._client = None
        self._threads.clear()

    async def on_task_start(self, data: TaskStart) -> None:
        self._evals[data.eval_id] = data.spec

    async def on_task_end(self, data: TaskEnd) -> None:
        self._evals.pop(data.eval_id, None)

    async def on_sample_start(self, data: SampleStart) -> None:
        assert self._client

        # create and enter thread
        thread_ctx = weave.thread(thread_id=data.sample_id)
        thread_ctx.__enter__()

        # create call
        call_name = (
            f"{self._evals[data.eval_id].task} ({data.summary.id}-{data.summary.epoch})"
        )
        call = self._client.create_call(
            call_name,
            inputs={"input": to_jsonable_python(data.summary.input)},
            attributes={
                "id": data.summary.id,
                "epoch": data.summary.epoch,
                "sample_metadata": data.summary.metadata,
            },
        )

        # track thread and call for cleanup
        self._threads[data.sample_id] = (thread_ctx, call)

    async def on_sample_end(self, data: SampleEnd) -> None:
        assert self._client

        thread_ctx, call = self._threads.pop(data.sample_id)
        self._client.finish_call(call, output=data.sample.output.model_dump())
        thread_ctx.__exit__(None, None, None)
