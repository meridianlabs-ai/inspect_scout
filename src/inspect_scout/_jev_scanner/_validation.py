from pydantic import JsonValue

from .._scanner.result import Result
from .._validation.predicates import PredicateFn
from .._validation.registry import validation_predicate


@validation_predicate
def prob_threshold(threshold: float = 0.5) -> PredicateFn:
    """Validation predicate comparing a probabilistic result to a boolean target.

    Treats a result as positive when its ``metadata["p"]`` (as produced by
    `jev_scanner()` boolean answers) is at or above ``threshold``, so the same
    scan can be validated at different operating points.

    Args:
        threshold: Probability at or above which the result counts as positive.

    Returns:
        A validation predicate.
    """
    if not 0.0 <= threshold <= 1.0:
        raise ValueError(f"threshold must be between 0 and 1 (got {threshold}).")

    async def predicate(result: Result, target: JsonValue) -> bool:
        p = (result.metadata or {}).get("p")
        if not isinstance(p, int | float):
            raise TypeError(
                "prob_threshold requires a result with a numeric metadata['p'] "
                "(e.g. a jev_scanner boolean answer)."
            )
        return (p >= threshold) == bool(target)

    return predicate
