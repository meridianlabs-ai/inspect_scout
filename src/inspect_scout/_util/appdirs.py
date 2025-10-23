from pathlib import Path

from inspect_ai._util.appdirs import package_data_dir

from inspect_scout._util.constants import PKG_NAME


def scout_data_dir(subdir: str) -> Path:
    return package_data_dir(PKG_NAME, subdir)
