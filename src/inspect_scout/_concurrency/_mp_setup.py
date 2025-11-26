"""Setup module for spawn subprocess - configures sys.path at import time."""

import json
import os
import sys

# This module is imported FIRST in subprocess, before any user code
# Read environment variables and configure subprocess before unpickling happens

# Module-level code runs at import time, but only in fresh subprocesses
# (not when imported in parent process before env vars are set)

if "INSPECT_SCOUT_SYS_PATH" in os.environ:
    sys_path = json.loads(os.environ["INSPECT_SCOUT_SYS_PATH"])
    sys.path[:] = sys_path  # Modify in place to preserve sys.path identity

# Add plugin directories to sys.path for user imports (scanjobs, scanners, etc.)
if "INSPECT_SCOUT_PLUGIN_DIRS" in os.environ:
    plugin_dirs = json.loads(os.environ["INSPECT_SCOUT_PLUGIN_DIRS"])
    for plugin_dir in plugin_dirs:
        if plugin_dir not in sys.path:
            sys.path.insert(0, plugin_dir)
