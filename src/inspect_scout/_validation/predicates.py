from typing import Awaitable, Callable, Literal, TypeAlias

from inspect_ai._util._async import is_callable_coroutine
from pydantic import JsonValue

from inspect_scout._scanner.result import Result

# Predicate function signatures
PredicateFn = Callable[[Result, JsonValue], Awaitable[bool | dict[str, bool]]]

# Union type for all validation predicates (strings + callables)
ValidationPredicate: TypeAlias = (
    Literal[
        "gt",
        "gte",
        "lt",
        "lte",
        "eq",
        "ne",
        "contains",
        "startswith",
        "endswith",
        "icontains",
        "iequals",
    ]
    | PredicateFn
)
"""Predicate used to compare scanner result with target value."""


# Numeric comparison predicates


async def _gt(result: Result, target: JsonValue) -> bool:
    """Greater than comparison."""
    if not isinstance(result.value, (int, float)):
        raise TypeError(
            f"gt predicate requires numeric value, got {type(result.value).__name__}"
        )
    if not isinstance(target, (int, float)):
        raise TypeError(
            f"gt predicate requires numeric target, got {type(target).__name__}"
        )
    return result.value > target


async def _gte(result: Result, target: JsonValue) -> bool:
    """Greater than or equal comparison."""
    if not isinstance(result.value, (int, float)):
        raise TypeError(
            f"gte predicate requires numeric value, got {type(result.value).__name__}"
        )
    if not isinstance(target, (int, float)):
        raise TypeError(
            f"gte predicate requires numeric target, got {type(target).__name__}"
        )
    return result.value >= target


async def _lt(result: Result, target: JsonValue) -> bool:
    """Less than comparison."""
    if not isinstance(result.value, (int, float)):
        raise TypeError(
            f"lt predicate requires numeric value, got {type(result.value).__name__}"
        )
    if not isinstance(target, (int, float)):
        raise TypeError(
            f"lt predicate requires numeric target, got {type(target).__name__}"
        )
    return result.value < target


async def _lte(result: Result, target: JsonValue) -> bool:
    """Less than or equal comparison."""
    if not isinstance(result.value, (int, float)):
        raise TypeError(
            f"lte predicate requires numeric value, got {type(result.value).__name__}"
        )
    if not isinstance(target, (int, float)):
        raise TypeError(
            f"lte predicate requires numeric target, got {type(target).__name__}"
        )
    return result.value <= target


async def _eq(result: Result, target: JsonValue) -> bool:
    """Equality comparison."""
    return result.value == target


async def _ne(result: Result, target: JsonValue) -> bool:
    """Not equal comparison."""
    return result.value != target


# String comparison predicates


async def _contains(result: Result, target: JsonValue) -> bool:
    """Substring contains comparison (case-sensitive)."""
    if not isinstance(result.value, str):
        raise TypeError(
            f"contains predicate requires string value, got {type(result.value).__name__}"
        )
    if not isinstance(target, str):
        raise TypeError(
            f"contains predicate requires string target, got {type(target).__name__}"
        )
    return target in result.value


async def _startswith(result: Result, target: JsonValue) -> bool:
    """Prefix match comparison."""
    if not isinstance(result.value, str):
        raise TypeError(
            f"startswith predicate requires string value, got {type(result.value).__name__}"
        )
    if not isinstance(target, str):
        raise TypeError(
            f"startswith predicate requires string target, got {type(target).__name__}"
        )
    return result.value.startswith(target)


async def _endswith(result: Result, target: JsonValue) -> bool:
    """Suffix match comparison."""
    if not isinstance(result.value, str):
        raise TypeError(
            f"endswith predicate requires string value, got {type(result.value).__name__}"
        )
    if not isinstance(target, str):
        raise TypeError(
            f"endswith predicate requires string target, got {type(target).__name__}"
        )
    return result.value.endswith(target)


async def _icontains(result: Result, target: JsonValue) -> bool:
    """Substring contains comparison (case-insensitive)."""
    if not isinstance(result.value, str):
        raise TypeError(
            f"icontains predicate requires string value, got {type(result.value).__name__}"
        )
    if not isinstance(target, str):
        raise TypeError(
            f"icontains predicate requires string target, got {type(target).__name__}"
        )
    return target.lower() in result.value.lower()


async def _iequals(result: Result, target: JsonValue) -> bool:
    """Equality comparison (case-insensitive)."""
    if not isinstance(result.value, str):
        raise TypeError(
            f"iequals predicate requires string value, got {type(result.value).__name__}"
        )
    if not isinstance(target, str):
        raise TypeError(
            f"iequals predicate requires string target, got {type(target).__name__}"
        )
    return result.value.lower() == target.lower()


# Registry of all built-in predicates
PREDICATES: dict[str, PredicateFn] = {
    "gt": _gt,
    "gte": _gte,
    "lt": _lt,
    "lte": _lte,
    "eq": _eq,
    "ne": _ne,
    "contains": _contains,
    "startswith": _startswith,
    "endswith": _endswith,
    "icontains": _icontains,
    "iequals": _iequals,
}


def resolve_predicate(
    predicate: ValidationPredicate | None,
) -> PredicateFn:
    """Resolve a predicate to a callable function.

    Args:
        predicate: Either a ValidationPredicate string name, a callable function, or None.

    Returns:
        A callable predicate function (either single or multi).

    Raises:
        ValueError: If the predicate string is not recognized.
        TypeError: If the predicate is not a valid type.
    """
    if predicate is None:
        return _eq
    if callable(predicate):
        if not is_callable_coroutine(predicate):
            raise TypeError("Validation predicates must be async functions.")
        return predicate
    if isinstance(predicate, str):
        if predicate not in PREDICATES:
            raise ValueError(
                f"Unknown predicate: {predicate}. Valid predicates: {', '.join(PREDICATES.keys())}"
            )
        return PREDICATES[predicate]
    raise TypeError(f"Invalid predicate type: {type(predicate).__name__}")
