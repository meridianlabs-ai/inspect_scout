## Unreleased

- Scanning: Switch from `dill` to `cloudpickle` and restore default `max_processes` to 4 after resolving multiprocessing serialization issues.

## 0.4.1 (12 December 2025)

- Scan jobs: Correct resolution order for options (CLI, then scanjob config, then environment variables).
- Scanning: Restore default `max_processes` to 1 while we resolve some multiprocessing serialization issues.

## 0.4.0 (11 December 2025)

- Initial release.
