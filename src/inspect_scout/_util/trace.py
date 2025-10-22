from pathlib import Path

from inspect_ai._util.appdirs import inspect_data_dir


def scout_trace_dir() -> Path:
    return inspect_data_dir("scout_traces")
