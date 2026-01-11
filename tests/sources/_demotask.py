from typing import Any

import dotenv
from inspect_ai import eval
from langfuse import get_client, observe, propagate_attributes
from shortuuid import uuid

dotenv.load_dotenv()


def run_eval(model: str, model_args: dict[str, Any] | None = None) -> None:
    eval(
        "inspect_evals/gdm_in_house_ctf",
        model=model,
        epochs=1,
        limit=1,
        model_args=model_args or {},
    )


@observe
def langfuse_task(model: str, model_args: dict[str, Any] | None = None) -> None:
    client = get_client()
    session_id = uuid()
    with propagate_attributes(
        session_id=session_id, metadata={"scout": "true"}, tags=["scout"]
    ):
        run_eval(model, model_args)
    client.flush()


# session_id: fu4epGBdMGZ84KXSCY6aWB
def langfuse_capture_anthropic() -> None:
    # pip install opentelemetry-instrumentation-anthropic
    from opentelemetry.instrumentation.anthropic import AnthropicInstrumentor

    AnthropicInstrumentor().instrument()
    langfuse_task("anthropic/claude-sonnet-4-5")


# session_id: LhXbgLJvb4KCsuDV5rffpR
def langfuse_capture_openai_completions() -> None:
    # pip install openinference-instrumentation-openai
    from openinference.instrumentation.openai import OpenAIInstrumentor

    OpenAIInstrumentor().instrument()
    langfuse_task("openai/gpt-5", {"responses_api": False})


# session_id: SsZiMRBMvPH5GPnsu6Jk69
def langfuse_capture_openai() -> None:
    # pip install openinference-instrumentation-openai
    from openinference.instrumentation.openai import OpenAIInstrumentor

    OpenAIInstrumentor().instrument()
    langfuse_task("openai/gpt-5.1-codex")


# session_id: EG2UfE9MvpBSmy73R6a2UH
def langfuse_capture_google() -> None:
    # pip install openinference-instrumentation-google-genai
    from openinference.instrumentation.google_genai import GoogleGenAIInstrumentor

    GoogleGenAIInstrumentor().instrument()
    langfuse_task("google/gemini-3-pro-preview")


if __name__ == "__main__":
    # langfuse_capture_anthropic()
    # langfuse_capture_openai()
    # langfuse_capture_openai_completions()
    # langfuse_capture_google()
    pass
