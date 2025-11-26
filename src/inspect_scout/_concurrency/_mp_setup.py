"""Setup module for spawn subprocess - runs at import time before unpickling."""

import json
import os
import sys

# This module is imported FIRST in subprocess, before any user code
# Read environment variables and configure subprocess before unpickling happens

if "INSPECT_SCOUT_SYS_PATH" in os.environ:
    sys_path = json.loads(os.environ["INSPECT_SCOUT_SYS_PATH"])
    sys.path[:] = sys_path  # Modify in place to preserve sys.path identity

if "INSPECT_SCOUT_WORKING_DIR" in os.environ:
    working_dir = os.environ["INSPECT_SCOUT_WORKING_DIR"]
    os.chdir(working_dir)
