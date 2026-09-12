"""Typed compatibility boundary for wrapt 1.x and 2.x."""

from typing import TYPE_CHECKING, Any, Callable, Generic, TypeVar

_ProxiedT = TypeVar("_ProxiedT")
_Wrapper = Callable[
    [Callable[..., Any], Any, tuple[Any, ...], dict[str, Any]],
    Any,
]

if TYPE_CHECKING:

    class TypedObjectProxy(Generic[_ProxiedT]):
        __wrapped__: _ProxiedT

        def __init__(self, wrapped: _ProxiedT) -> None: ...

    def wrap_function_wrapper(
        target: str,
        name: str,
        wrapper: _Wrapper,
    ) -> object: ...

else:
    from wrapt import ObjectProxy
    from wrapt import wrap_function_wrapper as wrap_function_wrapper

    # Generic supplies runtime subscription because wrapt 1.x's proxy does not.
    class TypedObjectProxy(ObjectProxy, Generic[_ProxiedT]):
        pass
