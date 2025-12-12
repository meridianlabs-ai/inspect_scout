import inspect
import re
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Counter, Literal, Sequence, TypeVar, cast, overload

from inspect_ai._util.config import read_config_object
from inspect_ai._util.decorator import parse_decorators
from inspect_ai._util.error import PrerequisiteError
from inspect_ai._util.file import file
from inspect_ai._util.module import load_module
from inspect_ai._util.package import get_installed_package_name
from inspect_ai._util.path import add_to_syspath, pretty_path
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
from inspect_ai.model import GenerateConfig, Model, ModelConfig, get_model
from inspect_ai.model._util import resolve_model_roles
from jsonschema import Draft7Validator
from pydantic import BaseModel, ConfigDict, Field

from inspect_scout._scanspec import ScannerSpec, Worklist
from inspect_scout._transcript.factory import transcripts_from
from inspect_scout._util.decorator import split_spec
from inspect_scout._validation.types import ValidationSet

from ._concurrency import _mp_common
from ._scanner.scanner import Scanner, scanner_create
from ._transcript.transcripts import Transcripts


class ScanJobConfig(BaseModel):
    """Scan job configuration."""

    name: str = Field(default="job")
    """Name of scan job (defaults to "job")."""

    transcripts: str | list[str] | None = Field(default=None)
    """Trasnscripts to scan."""

    scanners: list[ScannerSpec] | dict[str, ScannerSpec] | None = Field(default=None)
    """Scanners to apply to transcripts."""

    worklist: list[Worklist] | None = Field(default=None)
    """Transcript ids to process for each scanner (defaults to processing all transcripts)."""

    validation: dict[str, ValidationSet] | None = Field(default=None)
    """Validation cases to apply for scanners."""

    results: str | None = Field(default=None)
    """Location to write results (filesystem or S3 bucket). Defaults to "./scans"."""

    model: str | None = Field(default=None)
    """Model to use for scanning by default (individual scanners can always call `get_model()` to us arbitrary models).

    If not specified use the value of the SCOUT_SCAN_MODEL environment variable.
    """

    model_base_url: str | None = Field(default=None)
    """Base URL for communicating with the model API.

    If not specified use the value of the SCOUT_SCAN_MODEL_BASE_URL environment variable.
    """

    model_args: dict[str, Any] | str | None = Field(default=None)
    """Model creation args (as a dictionary or as a path to a JSON or YAML config file).

    If not specified use the value of the SCOUT_SCAN_MODEL_ARGS environment variable.
    """

    generate_config: GenerateConfig | None = Field(default=None)
    """`GenerationConfig` for calls to the model."""

    model_roles: dict[str, ModelConfig | str] | None = Field(default=None)
    """Named roles for use in `get_model()`."""

    max_transcripts: int | None = Field(default=None)
    """The maximum number of transcripts to process concurrently (this also serves as the default value for `max_connections`). Defaults to 25."""

    max_processes: int | None = Field(default=None)
    """The maximum number of concurrent processes (for multiproccesing). Defaults to 4."""

    limit: int | None = Field(default=None)
    """Limit the number of transcripts processed."""

    shuffle: bool | int | None = Field(default=None)
    """Shuffle the order of transcripts (pass an `int` to set a seed for shuffling)."""

    tags: list[str] | None = Field(default=None)
    """One or more tags for this scan."""

    metadata: dict[str, Any] | None = Field(default=None)
    """Metadata for this scan."""

    log_level: (
        Literal[
            "debug", "http", "sandbox", "info", "warning", "error", "critical", "notset"
        ]
        | None
    ) = Field(default=None)
    """Level for logging to the console: "debug", "http", "sandbox", "info", "warning", "error", "critical", or "notset" (defaults to "warning")."""

    model_config = ConfigDict(extra="forbid", protected_namespaces=())


class ScanJob:
    """Scan job definition."""

    def __init__(
        self,
        *,
        transcripts: Transcripts | None = None,
        scanners: Sequence[Scanner[Any] | tuple[str, Scanner[Any]]]
        | dict[str, Scanner[Any]],
        worklist: Sequence[Worklist] | None = None,
        validation: dict[str, ValidationSet] | None = None,
        results: str | None = None,
        model: str | Model | None = None,
        model_base_url: str | None = None,
        model_args: dict[str, Any] | None = None,
        generate_config: GenerateConfig | None = None,
        model_roles: dict[str, str | Model] | None = None,
        max_transcripts: int | None = None,
        max_processes: int | None = None,
        limit: int | None = None,
        shuffle: bool | int | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        log_level: str | None = None,
        name: str | None = None,
    ):
        # save transcripts and name
        self._transcripts = transcripts
        self._worklist = worklist
        self._validation = validation
        self._name = name
        self._results = results
        self._model = (
            get_model(
                model,
                config=generate_config or GenerateConfig(),
                base_url=model_base_url,
                **(model_args or {}),
            )
            if model is not None
            else None
        )
        self._model_base_url = model_base_url
        self._model_args = model_args
        self._generate_config = generate_config
        self._model_roles = resolve_model_roles(model_roles)
        self._max_transcripts = max_transcripts
        self._max_processes = max_processes
        self._limit = limit
        self._shuffle = shuffle
        self._tags = tags
        self._metadata = metadata
        self._log_level = log_level

        # resolve scanners and candidate names (we will ensure no duplicates)
        if isinstance(scanners, dict):
            named_scanners: list[tuple[str, Scanner[Any]]] = list(scanners.items())
        else:
            named_scanners = [
                scanner
                if isinstance(scanner, tuple)
                else (registry_unqualified_name(scanner), scanner)
                for scanner in scanners
            ]

        # now built the dict, adding a numeric suffix for duplicated names
        self._scanners: dict[str, Scanner[Any]] = {}
        name_counts = Counter(t[0] for t in named_scanners)
        current_counts: dict[str, int] = {k: 0 for k in name_counts.keys()}
        for name, scanner in named_scanners:
            name = safe_scanner_name(name)
            if name_counts[name] > 1:
                current_counts[name] = current_counts[name] + 1
                name = f"{name}_{current_counts[name]}"
            self._scanners[name] = scanner

    @staticmethod
    def from_config(config: ScanJobConfig) -> "ScanJob":
        from inspect_scout._scancontext import _scanners_from_spec, scanner_from_spec

        # base config
        kwargs = config.model_dump(exclude_none=True)

        # realize scanners
        if isinstance(config.scanners, list):
            kwargs["scanners"] = [
                scanner_from_spec(scanner) for scanner in config.scanners
            ]
        elif isinstance(config.scanners, dict):
            kwargs["scanners"] = _scanners_from_spec(config.scanners)

        # realize transcripts
        if config.transcripts is not None:
            kwargs["transcripts"] = transcripts_from(config.transcripts)

        # realize generate_config
        if config.generate_config is not None:
            kwargs["generate_config"] = GenerateConfig.model_validate(
                config.generate_config
            )

        return ScanJob(**kwargs)

    @property
    def name(self) -> str:
        """Name of scan job (defaults to @scanjob function name)."""
        if self._name is not None:
            return self._name
        elif is_registry_object(self):
            return registry_info(self).name
        else:
            return "scan"

    @property
    def transcripts(self) -> Transcripts | None:
        """Trasnscripts to scan."""
        return self._transcripts

    @property
    def worklist(self) -> Sequence[Worklist] | None:
        """Transcript ids to process for each scanner (defaults to processing all transcripts)."""
        return self._worklist

    @property
    def validation(self) -> dict[str, ValidationSet] | None:
        """Validation cases to apply."""
        return self._validation

    @property
    def scanners(self) -> dict[str, Scanner[Any]]:
        """Scanners to apply to transcripts."""
        return self._scanners

    @property
    def results(self) -> str | None:
        """Location to write results (filesystem or S3 bucket). Defaults to "./scans"."""
        return self._results

    @property
    def model(self) -> Model | None:
        """Model to use for scanning by default (individual scanners can always call `get_model()` to us arbitrary models).

        If not specified use the value of the SCOUT_SCAN_MODEL environment variable.
        """
        return self._model

    @property
    def model_base_url(self) -> str | None:
        """Base URL for communicating with the model API."""
        return self._model_base_url

    @property
    def model_args(self) -> dict[str, Any] | None:
        """Model creation args (as a dictionary or as a path to a JSON or YAML config file)."""
        return self._model_args

    @property
    def generate_config(self) -> GenerateConfig | None:
        """`GenerationConfig` for calls to the model."""
        return self._generate_config

    @property
    def model_roles(self) -> dict[str, Model] | None:
        """Named roles for use in `get_model()`."""
        return self._model_roles

    @property
    def max_transcripts(self) -> int | None:
        """The maximum number of transcripts to process concurrently (this also serves as the default value for `max_connections`). Defaults to 25."""
        return self._max_transcripts

    @property
    def max_processes(self) -> int | None:
        """The maximum number of concurrent processes (for multiproccesing). Defaults to 4."""
        return self._max_processes

    @property
    def limit(self) -> int | None:
        """Limit the number of transcripts processed."""
        return self._limit

    @property
    def shuffle(self) -> bool | int | None:
        """Shuffle the order of transcripts (pass an `int` to set a seed for shuffling)."""
        return self._shuffle

    @property
    def tags(self) -> list[str] | None:
        """One or more tags for this scan."""
        return self._tags

    @property
    def metadata(self) -> dict[str, Any] | None:
        """Metadata for this scan."""
        return self._metadata

    @property
    def log_level(self) -> str | None:
        """Level for logging to the console: "debug", "http", "sandbox", "info", "warning", "error", "critical", or "notset" (defaults to "warning")."""
        return self._log_level


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
      func: Function returning `ScanJob`.
      name: Optional name for scanjob (defaults to function name).

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
                file = inspect.getfile(scanjob_type)
                if file:
                    setattr(scanjob_instance, SCANJOB_FILE_ATTR, Path(file).as_posix())

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


def scanjob_from_cli_spec(spec: str, scanjob_args: dict[str, Any]) -> ScanJob | None:
    # only look if its a package reference
    if "/" not in spec:
        return None

    # scan job in registry
    o = registry_lookup("scanjob", spec)
    if o is not None:
        return scanjob_create(spec, scanjob_args)

    # scanner in registry
    o = registry_lookup("scanner", spec)
    if o is not None:
        scanner = scanner_create(spec, scanjob_args)
        return ScanJob(transcripts=None, scanners=[scanner])

    # nothing
    return None


def scanjob_from_file(file: str, scanjob_args: dict[str, Any]) -> ScanJob | None:
    # split out name
    file, job = split_spec(file)

    # compute path
    scanjob_path = Path(file).resolve()

    # check for existence
    if not scanjob_path.exists():
        raise PrerequisiteError(f"The file '{pretty_path(file)}' does not exist.")

    # load from config or python decorated functions
    if scanjob_path.suffix in [".json", ".yml", ".yaml"]:
        return scanjob_from_config_file(scanjob_path)
    else:
        # add scanjob directory to sys.path for imports
        scanjob_dir = scanjob_path.parent.as_posix()

        with add_to_syspath(scanjob_dir):
            load_module(scanjob_path)
            decorator_names = [
                deco[0] for deco in parse_decorators(scanjob_path, "scanjob")
            ]

            if job is not None and job in decorator_names:
                job_name = job
            elif len(decorator_names) > 1:
                raise PrerequisiteError(
                    f"More than one @scanjob decorated function found in '{file}. Please use file@job to designate a specific job"
                )
            elif job is None and len(decorator_names) == 1:
                job_name = decorator_names[0]
            else:
                return None

            _mp_common.register_plugin_directory(scanjob_dir)
            return scanjob_create(job_name, scanjob_args)


def scanjob_create(name: str, params: dict[str, Any]) -> ScanJob:
    obj = registry_lookup("scanjob", name)
    assert callable(obj)
    kwargs = registry_kwargs(**params)
    return cast(ScanJob, obj(**kwargs))


def scanjob_from_config_file(config: Path) -> ScanJob:
    # read config object
    with file(config.as_posix(), "r") as f:
        scanjob_config = read_config_object(f.read())

    # validate schema before deserializing
    schema = ScanJobConfig.model_json_schema(mode="validation")
    validator = Draft7Validator(schema)
    errors = list(validator.iter_errors(scanjob_config))
    if errors:
        message = "\n".join(
            [
                f"Found validation errors parsing scan job config from {pretty_path(config.as_posix())}:"
            ]
            + [f"- {error.message}" for error in errors]
        )
        raise PrerequisiteError(message)

    return ScanJob.from_config(ScanJobConfig.model_validate(scanjob_config))


def safe_scanner_name(scanner: str, max_length: int = 55) -> str:
    """
    Convert scanner name to a safe identifier for filesystems and SQL table names.

    Args:
        scanner: The scanner name to sanitize
        max_length: Maximum length for the result (default: 55 as there could be a
            disambiguating suffix and PostgreSQL limits table names to 63)

    Returns:
        A lowercase string with only alphanumeric characters and underscores

    Raises:
        ValueError: If the result would be empty or invalid
    """
    if not scanner or not scanner.strip():
        raise ValueError("Scanner name cannot be empty")

    # Replace any non-alphanumeric character with underscore
    safe = re.sub(r"[^a-zA-Z0-9]+", "_", scanner)

    # Convert to lowercase
    safe = safe.lower()

    # Remove leading/trailing underscores
    safe = safe.strip("_")

    # Ensure it doesn't start with a number
    if safe and safe[0].isdigit():
        safe = "scanner_" + safe

    # Truncate to max_length
    safe = safe[:max_length]

    # Check for SQL reserved words (simplified example)
    sql_reserved = {"select", "table", "from", "where", "insert", "delete"}
    if safe in sql_reserved:
        safe = f"scanner_{safe}"

    if not safe:
        raise ValueError(f"Cannot create safe name from: {scanner}")

    return safe
