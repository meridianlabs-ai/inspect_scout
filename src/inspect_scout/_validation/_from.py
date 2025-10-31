from pathlib import Path

import pandas as pd
from upath import UPath

from .types import Validation


def validation_from(file: str | Path | UPath | pd.DataFrame) -> Validation:
    """Read validation cases from a file or data frame.

    Args:
        file: Path to a CSV, YAML, JSON, or JSONL file with validation cases, or data frame with validation cases.
    """
    return Validation(cases=[])
