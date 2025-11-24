import hooks  # type: ignore[import-not-found]  # noqa: F401
from inspect_ai import eval
from inspect_evals.mmlu_pro import mmlu_pro

eval(mmlu_pro(), limit=10, model="openai/gpt-5-mini", display="plain")
