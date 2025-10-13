import inspect
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Counter, Sequence, TypeVar, cast, overload

from inspect_ai._util.decorator import parse_decorators
from inspect_ai._util.error import PrerequisiteError
from inspect_ai._util.module import load_module
from inspect_ai._util.package import get_installed_package_name
from inspect_ai._util.path import chdir_python, pretty_path
from inspect_ai._util.registry import (
    RegistryInfo,
    is_registry_object,
    registry_add,
    registry_info,
    registry_kwargs,
    registry_lookup,
    registry_name,
    registry_tag,
    registry_unqualified_name,
)

from ._scanner.scanner import Scanner
from ._scanner.types import ScannerInput
from ._transcript.transcripts import Transcripts


class ScanJob:
    def __init__(
        self,
        *,
        transcripts: Transcripts | None = None,
        scanners: Sequence[Scanner[ScannerInput] | tuple[str, Scanner[ScannerInput]]]
        | dict[str, Scanner[ScannerInput]],
        name: str | None = None,
    ):
        # save transcripts and name
        self._trancripts = transcripts
        self._name = name

        # resolve scanners and candidate names (we will ensure no duplicates)
        if isinstance(scanners, dict):
            named_scanners: list[tuple[str, Scanner[ScannerInput]]] = list(
                scanners.items()
            )
        else:
            named_scanners = [
                scanner
                if isinstance(scanner, tuple)
                else (registry_unqualified_name(scanner), scanner)
                for scanner in scanners
            ]

        # now built the dict, adding a numeric suffix for duplicated names
        self._scanners: dict[str, Scanner[ScannerInput]] = {}
        name_counts = Counter(t[0] for t in named_scanners)
        current_counts: dict[str, int] = {k: 0 for k in name_counts.keys()}
        for name, scanner in named_scanners:
            if name == "transcripts":
                raise ValueError(
                    "'transcripts' is a name reserved for results so cannot be used as scanner name"
                )
            if name_counts[name] > 1:
                current_counts[name] = current_counts[name] + 1
                name = f"{name}_{current_counts[name]}"
            self._scanners[name] = scanner

    @property
    def name(self) -> str:
        if self._name is not None:
            return self._name
        elif is_registry_object(self):
            return registry_info(self).name
        else:
            return "scan"

    @property
    def transcripts(self) -> Transcripts | None:
        return self._trancripts

    @property
    def scanners(self) -> dict[str, Scanner[ScannerInput]]:
        return self._scanners


ScanJobType = TypeVar("ScanJobType", bound=Callable[..., ScanJob])

SCANJOB_FILE_ATTR = "__scanjob_file__"


@overload
def scanjob(func: ScanJobType) -> ScanJobType: ...


@overload
def scanjob(
    *,
    name: str | None = ...,
) -> Callable[[ScanJobType], ScanJobType]: ...


def scanjob(
    func: ScanJobType | None = None, *, name: str | None = None
) -> ScanJobType | Callable[[ScanJobType], ScanJobType]:
    r"""Decorator for registering scan jobs.

    Args:
      func: Function returning `ScanJob` targeted by
        plain task decorator without attributes (e.g. `@scanjob`)
      name:
        Optional name for scanjob. If the decorator has no name
        argument then the name of the function
        will be used to automatically assign a name.

    Returns:
        ScanJob with registry attributes.
    """

    def create_scanjob_wrapper(scanjob_type: ScanJobType) -> ScanJobType:
        # Get the name and parameters of the task
        scanjob_name = registry_name(scanjob_type, name or scanjob_type.__name__)
        params = list(inspect.signature(scanjob_type).parameters.keys())

        # Create and return the wrapper function
        @wraps(scanjob_type)
        def wrapper(*w_args: Any, **w_kwargs: Any) -> ScanJob:
            # Create the scanjob
            scanjob_instance = scanjob_type(*w_args, **w_kwargs)

            # Tag the task with registry information
            registry_tag(
                scanjob_type,
                scanjob_instance,
                RegistryInfo(
                    type="scanjob",
                    name=scanjob_name,
                    metadata=dict(params=params),
                ),
                *w_args,
                **w_kwargs,
            )

            # if its not from an installed package then it is a "local"
            # module import, so set its task file and run dir
            if get_installed_package_name(scanjob_type) is None:
                module = inspect.getmodule(scanjob_type)
                if module and hasattr(module, "__file__") and module.__file__:
                    file = Path(module.__file__)
                    setattr(scanjob_instance, SCANJOB_FILE_ATTR, file.as_posix())

            # Return the task instance
            return scanjob_instance

        # functools.wraps overrides the return type annotation of the inner function, so
        # we explicitly set it again
        wrapper.__annotations__["return"] = ScanJob

        # Register the task and return the wrapper
        wrapped_scanjob_type = cast(ScanJobType, wrapper)
        registry_add(
            wrapped_scanjob_type,
            RegistryInfo(
                type="scanjob",
                name=scanjob_name,
                metadata=(dict(params=params)),
            ),
        )
        return wrapped_scanjob_type

    if func:
        return create_scanjob_wrapper(func)
    else:
        # The decorator was used with arguments: @scanjob(name="foo")
        def decorator(func: ScanJobType) -> ScanJobType:
            return create_scanjob_wrapper(func)

        return decorator


def scanjob_from_file(file: str, scanjob_args: dict[str, Any]) -> ScanJob | None:
    # compute path
    scanjob_path = Path(file).resolve()

    # check for existence
    if not scanjob_path.exists():
        raise PrerequisiteError(f"The file '{pretty_path(file)}' does not exist.")

    # switch contexts for load
    with chdir_python(scanjob_path.parent.as_posix()):
        # create scanjob
        load_module(scanjob_path)
        scanjob_decorators = parse_decorators(scanjob_path, "scanjob")
        if len(scanjob_decorators) > 1:
            raise PrerequisiteError(
                f"More than one @scanjob decorated function found in '{file}"
            )
        elif len(scanjob_decorators) == 1:
            return scanjob_create(scanjob_decorators[0][0], scanjob_args)
        else:
            return None


def scanjob_create(name: str, params: dict[str, Any]) -> ScanJob:
    obj = registry_lookup("scanjob", name)
    assert callable(obj)
    kwargs = registry_kwargs(**params)
    return cast(ScanJob, obj(**kwargs))
