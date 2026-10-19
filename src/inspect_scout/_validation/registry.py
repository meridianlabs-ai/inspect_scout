from __future__ import annotations

import inspect
from collections.abc import Callable
from functools import wraps
from pathlib import Path
from typing import Any, ParamSpec, cast, overload

from inspect_ai._util.package import get_installed_package_name
from inspect_ai._util.registry import (
    RegistryInfo,
    is_registry_object,
    registry_add,
    registry_info,
    registry_kwargs,
    registry_lookup,
    registry_name,
    registry_params,
    registry_tag,
)

from .predicates import PredicateFn, ValidationPredicate, is_async_predicate

P = ParamSpec("P")
PredicateFactory = Callable[P, ValidationPredicate]
RegisteredPredicateFactory = Callable[P, PredicateFn]
PREDICATE_FILE_ATTR = "__validation_predicate_file__"


@overload
def validation_predicate(
    factory: PredicateFactory[P],
) -> RegisteredPredicateFactory[P]: ...


@overload
def validation_predicate(
    *, name: str | None = ...
) -> Callable[[PredicateFactory[P]], RegisteredPredicateFactory[P]]: ...


def validation_predicate(
    factory: PredicateFactory[P] | None = None,
    *,
    name: str | None = None,
) -> (
    RegisteredPredicateFactory[P]
    | Callable[[PredicateFactory[P]], RegisteredPredicateFactory[P]]
):
    """Register a portable custom validation predicate.

    Registered predicates are persisted by name and Inspect registry-compatible
    creation parameters rather than by serializing their Python implementation.

    Args:
        factory: Function that creates an async validation predicate.
        name: Optional registered name (defaults to the factory name).

    Returns:
        A registered predicate factory.
    """

    def decorate(factory_fn: PredicateFactory[P]) -> RegisteredPredicateFactory[P]:
        predicate_base_name = name or str(getattr(factory_fn, "__name__", "predicate"))
        predicate_name = registry_name(
            factory_fn,
            predicate_base_name,
        )

        @wraps(factory_fn)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> PredicateFn:
            predicate = factory_fn(*args, **kwargs)
            if isinstance(predicate, str) or not is_async_predicate(predicate):
                raise TypeError(
                    f"Validation predicate '{predicate_name}' must be an async callable."
                )

            registry_tag(
                factory_fn,
                predicate,
                RegistryInfo(
                    type="validation_predicate",
                    name=predicate_name,
                ),
                *args,
                **kwargs,
            )

            if get_installed_package_name(factory_fn) is None:
                file = inspect.getfile(factory_fn)
                if file and Path(file).is_file():
                    setattr(predicate, PREDICATE_FILE_ATTR, Path(file).as_posix())

            return predicate

        registered = cast(RegisteredPredicateFactory[P], wrapper)
        registry_add(
            registered,
            RegistryInfo(
                type="validation_predicate",
                name=predicate_name,
            ),
        )
        return registered

    if factory is not None:
        return decorate(factory)
    return decorate


def is_registered_predicate(predicate: object) -> bool:
    """Return whether a predicate was created by `@validation_predicate`."""
    return is_registry_object(predicate, "validation_predicate")


def registered_predicate_name(predicate: PredicateFn) -> str:
    """Return the registered name for a predicate instance."""
    return registry_info(predicate).name


def registered_predicate_params(predicate: PredicateFn) -> dict[str, Any]:
    """Return the arguments used to create a registered predicate."""
    return registry_params(predicate)


def registered_predicate_file(predicate: PredicateFn) -> str | None:
    """Return the local source file for a registered predicate, if any."""
    return cast(str | None, getattr(predicate, PREDICATE_FILE_ATTR, None))


def create_registered_predicate(name: str, params: dict[str, Any]) -> PredicateFn:
    """Create a registered predicate by name and arguments."""
    factory = registry_lookup("validation_predicate", name)
    if not callable(factory):
        raise ValueError(
            f"Validation predicate '{name}' was not found. Ensure its module "
            "is imported or its package is registered as an Inspect extension."
        )

    return cast(PredicateFn, factory(**registry_kwargs(**params)))
