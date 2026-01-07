from typing import Any, Literal, Type

from inspect_ai.model import GenerateConfig, ModelConfig
from pydantic import BaseModel, ConfigDict, Field, model_validator

from inspect_scout._scanspec import ScannerSpec, Worklist
from inspect_scout._util.deprecation import raise_results_error, show_results_warning
from inspect_scout._validation.types import ValidationSet


class ScanJobConfig(BaseModel):
    """Scan job configuration."""

    name: str = Field(default="job")
    """Name of scan job (defaults to "job")."""

    transcripts: str | None = Field(default=None)
    """Trasnscripts to scan."""

    filter: str | list[str] = Field(default_factory=list)
    """SQL WHERE clause(s) for filtering transcripts."""

    scanners: list[ScannerSpec] | dict[str, ScannerSpec] | None = Field(default=None)
    """Scanners to apply to transcripts."""

    worklist: list[Worklist] | None = Field(default=None)
    """Transcript ids to process for each scanner (defaults to processing all transcripts)."""

    validation: dict[str, str | ValidationSet] | None = Field(default=None)
    """Validation cases to apply for scanners."""

    scans: str | None = Field(default=None)
    """Location to write scan results (filesystem or S3 bucket). Defaults to "./scans"."""

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

    results: str | None = Field(default=None)
    """Deprecated. Please use 'scans' instead."""

    @model_validator(mode="before")
    @classmethod
    def convert_results_to_scans(cls: Type["ScanJobConfig"], values: Any) -> Any:
        if not isinstance(values, dict):
            return values
        if "results" in values:
            # There cannot be a scans property too
            if "scans" in values:
                raise_results_error()

            # show warning
            show_results_warning()

            # copy to scans
            values["scans"] = values["results"]

        return values

    model_config = ConfigDict(extra="forbid", protected_namespaces=())
