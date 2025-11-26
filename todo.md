# Fork to Spawn Conversion - COMPLETED ✅

## Final Solution: Environment Variables at Import Time

Successfully converted multi-process strategy from fork to spawn using standard `multiprocessing` + `dill` + **environment variables**.

## The Critical Insight

**Problem:** When Python spawns a subprocess, it unpickles function arguments BEFORE entering the function. Setting sys.path inside the function is too late.

**Solution:** Use environment variables that are read at MODULE IMPORT TIME, before any unpickling happens.

## Implementation

### 1. New Setup Module (_mp_setup.py)
```python
import json, os, sys

# Read environment and configure BEFORE any imports
if "INSPECT_SCOUT_SYS_PATH" in os.environ:
    sys.path[:] = json.loads(os.environ["INSPECT_SCOUT_SYS_PATH"])
if "INSPECT_SCOUT_WORKING_DIR" in os.environ:
    os.chdir(os.environ["INSPECT_SCOUT_WORKING_DIR"])
```

### 2. Import Setup First (_mp_subprocess.py:12)
```python
# IMPORTANT: Import _mp_setup FIRST before anything else
from . import _mp_setup  # noqa: F401
```

### 3. Set Environment Variables (multi_process.py:274-275)
```python
os.environ["INSPECT_SCOUT_SYS_PATH"] = json.dumps(sys.path)
os.environ["INSPECT_SCOUT_WORKING_DIR"] = os.getcwd()
```

### 4. Use DillCallable for Closures (_mp_common.py)
Wrap closures so they can be pickled with user module references.

## Files Modified
1. **_mp_setup.py** (NEW) - reads env vars at import time
2. **_mp_subprocess.py** - imports _mp_setup first
3. **_mp_common.py** - added DillCallable wrapper
4. **multi_process.py** - sets env vars, uses spawn, wraps callables

## Test Results
✅ All 41 multi-process tests pass
✅ Works on Python 3.14
✅ No multiprocess dependency
✅ User modules importable (sys.path set before unpickling)

## Key Lesson
With spawn multiprocessing, you cannot set sys.path by passing it as an argument - by the time your function receives it, unpickling has already happened. Use environment variables that are read at module import time instead.
