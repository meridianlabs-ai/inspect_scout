import inspect
from typing import Callable, TypeVar, get_type_hints

F = TypeVar("F", bound=Callable[..., object])


def split_spec(spec: str) -> tuple[str, str | None]:
    parts = spec.rsplit("@", 1)
    if len(parts) == 2:
        return parts[0], parts[1]
    else:
        return spec, None


def fixup_wrapper_annotations(
    wrapper: F,
    wrapped: Callable[..., object],
    return_type: object | None = None,
) -> F:
    """Fix up type annotations on a wrapper function.

    When using `from __future__ import annotations` (PEP 563), annotations are
    stored as strings rather than actual type objects. This function resolves
    those strings to actual types and copies the signature from the wrapped
    function to the wrapper.

    Args:
        wrapper: The wrapper function to fix up.
        wrapped: The original wrapped function.
        return_type: Optional return type to set on the wrapper. If None,
            the return type from the wrapped function is used.

    Returns:
        The wrapper function with fixed annotations and signature.
    """
    wrapper.__annotations__ = get_type_hints(wrapped, wrapped.__globals__)
    if return_type is not None:
        wrapper.__annotations__["return"] = return_type
    wrapper.__signature__ = inspect.signature(wrapped)  # type: ignore[attr-defined]
    return wrapper
