import inspect
from typing import Callable, Literal, TypeAlias

from pydantic import JsonValue

# Predicate function signatures
SinglePredicateFn = Callable[[JsonValue, JsonValue], bool]
MultiPredicateFn = Callable[
    [dict[str, JsonValue], dict[str, JsonValue]], dict[str, bool]
]

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
    | SinglePredicateFn
    | MultiPredicateFn
)


# Numeric comparison predicates


def _gt(value: JsonValue, target: JsonValue) -> bool:
    """Greater than comparison."""
    if not isinstance(value, (int, float)):
        raise TypeError(
            f"gt predicate requires numeric value, got {type(value).__name__}"
        )
    if not isinstance(target, (int, float)):
        raise TypeError(
            f"gt predicate requires numeric target, got {type(target).__name__}"
        )
    return value > target


def _gte(value: JsonValue, target: JsonValue) -> bool:
    """Greater than or equal comparison."""
    if not isinstance(value, (int, float)):
        raise TypeError(
            f"gte predicate requires numeric value, got {type(value).__name__}"
        )
    if not isinstance(target, (int, float)):
        raise TypeError(
            f"gte predicate requires numeric target, got {type(target).__name__}"
        )
    return value >= target


def _lt(value: JsonValue, target: JsonValue) -> bool:
    """Less than comparison."""
    if not isinstance(value, (int, float)):
        raise TypeError(
            f"lt predicate requires numeric value, got {type(value).__name__}"
        )
    if not isinstance(target, (int, float)):
        raise TypeError(
            f"lt predicate requires numeric target, got {type(target).__name__}"
        )
    return value < target


def _lte(value: JsonValue, target: JsonValue) -> bool:
    """Less than or equal comparison."""
    if not isinstance(value, (int, float)):
        raise TypeError(
            f"lte predicate requires numeric value, got {type(value).__name__}"
        )
    if not isinstance(target, (int, float)):
        raise TypeError(
            f"lte predicate requires numeric target, got {type(target).__name__}"
        )
    return value <= target


def _eq(value: JsonValue, target: JsonValue) -> bool:
    """Equality comparison."""
    return value == target


def _ne(value: JsonValue, target: JsonValue) -> bool:
    """Not equal comparison."""
    return value != target


# String comparison predicates


def _contains(value: JsonValue, target: JsonValue) -> bool:
    """Substring contains comparison (case-sensitive)."""
    if not isinstance(value, str):
        raise TypeError(
            f"contains predicate requires string value, got {type(value).__name__}"
        )
    if not isinstance(target, str):
        raise TypeError(
            f"contains predicate requires string target, got {type(target).__name__}"
        )
    return target in value


def _startswith(value: JsonValue, target: JsonValue) -> bool:
    """Prefix match comparison."""
    if not isinstance(value, str):
        raise TypeError(
            f"startswith predicate requires string value, got {type(value).__name__}"
        )
    if not isinstance(target, str):
        raise TypeError(
            f"startswith predicate requires string target, got {type(target).__name__}"
        )
    return value.startswith(target)


def _endswith(value: JsonValue, target: JsonValue) -> bool:
    """Suffix match comparison."""
    if not isinstance(value, str):
        raise TypeError(
            f"endswith predicate requires string value, got {type(value).__name__}"
        )
    if not isinstance(target, str):
        raise TypeError(
            f"endswith predicate requires string target, got {type(target).__name__}"
        )
    return value.endswith(target)


def _icontains(value: JsonValue, target: JsonValue) -> bool:
    """Substring contains comparison (case-insensitive)."""
    if not isinstance(value, str):
        raise TypeError(
            f"icontains predicate requires string value, got {type(value).__name__}"
        )
    if not isinstance(target, str):
        raise TypeError(
            f"icontains predicate requires string target, got {type(target).__name__}"
        )
    return target.lower() in value.lower()


def _iequals(value: JsonValue, target: JsonValue) -> bool:
    """Equality comparison (case-insensitive)."""
    if not isinstance(value, str):
        raise TypeError(
            f"iequals predicate requires string value, got {type(value).__name__}"
        )
    if not isinstance(target, str):
        raise TypeError(
            f"iequals predicate requires string target, got {type(target).__name__}"
        )
    return value.lower() == target.lower()


# Registry of all built-in predicates
PREDICATES: dict[str, SinglePredicateFn] = {
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


def get_predicate_type(
    predicate: ValidationPredicate | None,
) -> Literal["string", "single", "multi", "none"]:
    """Detect the type of predicate.

    Args:
        predicate: A ValidationPredicate (string, callable, or None)

    Returns:
        "string" if it's a string literal predicate
        "single" if it's a single-value callable
        "multi" if it's a multi-value callable
        "none" if it's None
    """
    if predicate is None:
        return "none"
    if isinstance(predicate, str):
        return "string"
    if callable(predicate):
        # Inspect the signature to determine if it's single or multi
        try:
            sig = inspect.signature(predicate)
            params = list(sig.parameters.values())
            return_annotation = sig.return_annotation

            # Check return annotation if available
            if return_annotation != inspect.Signature.empty:
                # If returns dict[str, bool], it's a multi predicate
                return_str = str(return_annotation)
                if "dict" in return_str.lower() and "bool" in return_str.lower():
                    return "multi"

            # Check first parameter annotation
            if len(params) >= 1 and params[0].annotation != inspect.Parameter.empty:
                param_str = str(params[0].annotation)
                # If first param is dict, it's a multi predicate
                if "dict" in param_str.lower():
                    return "multi"

            # Default to single if we can't determine
            return "single"
        except (ValueError, TypeError):
            # If signature inspection fails, assume single
            return "single"
    return "none"


def resolve_predicate(
    predicate: ValidationPredicate | None,
) -> SinglePredicateFn | MultiPredicateFn:
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
        return predicate
    if isinstance(predicate, str):
        if predicate not in PREDICATES:
            raise ValueError(
                f"Unknown predicate: {predicate}. Valid predicates: {', '.join(PREDICATES.keys())}"
            )
        return PREDICATES[predicate]
    raise TypeError(f"Invalid predicate type: {type(predicate).__name__}")
