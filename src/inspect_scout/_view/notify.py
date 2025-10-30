import json
import os
from pathlib import Path
from urllib.parse import urlparse

from inspect_ai._util.vscode import vscode_workspace_id

from inspect_scout._util.appdirs import scout_data_dir

# lightweight tracking of when the last scan completed
# this enables the scout client to poll for changes frequently
# (e.g. every 1 second) with very minimal overhead.


def view_notify_scan(location: str) -> None:
    # do not do this when running under pytest
    if os.environ.get("PYTEST_VERSION", None) is not None:
        return

    file = view_last_scan_file()
    with open(file, "w", encoding="utf-8") as f:
        if not urlparse(location).scheme:
            location = Path(location).absolute().as_posix()

        # Construct a payload with context for the last eval
        payload = {
            "location": location,
        }
        workspace_id = vscode_workspace_id()
        if workspace_id:
            payload["workspace_id"] = workspace_id

        # Serialize the payload and write it to the signal file
        payload_json = json.dumps(payload, indent=2)
        f.write(payload_json)


def view_last_scan_time() -> int:
    file = view_last_scan_file()
    if file.exists():
        return int(file.stat().st_mtime * 1000)
    else:
        return 0


def view_data_dir() -> Path:
    return scout_data_dir("view")


def view_last_scan_file() -> Path:
    return view_data_dir() / "last-scan"
