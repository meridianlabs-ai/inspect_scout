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

if "INSPECT_SCOUT_WORKING_DIR" in os.environ:
    working_dir = os.environ["INSPECT_SCOUT_WORKING_DIR"]
    os.chdir(working_dir)

    # CRITICAL: Add working directory to sys.path for user scanner imports
    # With spawn, cwd is not automatically in sys.path like it is with fork
    if working_dir not in sys.path:
        sys.path.insert(0, working_dir)
