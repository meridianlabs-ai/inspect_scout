import os
from contextlib import ExitStack

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
from weave.trace.weave_client import WeaveClient


@hooks(name="weave_hooks", description="Weights & Biases Weave")
class WeaveHooks(Hooks):
    def __init__(self) -> None:
        self._client: WeaveClient | None = None
        self._evals: dict[str, EvalSpec] = {}
        self._threads: dict[str, ExitStack] = {}

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

        # create exit stack
        exit_stack = ExitStack()
        exit_stack.__enter__()
        exit_stack.enter_context(weave.thread(thread_id=data.sample_id))
        exit_stack.enter_context(
            weave.attributes(
                {
                    "id": data.summary.id,
                    "epoch": data.summary.epoch,
                    "sample_metadata": data.summary.metadata,
                }
            )
        )

        # track exit stack for cleanup
        self._threads[data.sample_id] = exit_stack

    async def on_sample_end(self, data: SampleEnd) -> None:
        assert self._client

        exit_stack = self._threads.pop(data.sample_id)
        exit_stack.__exit__(None, None, None)
