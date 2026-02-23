
You may want to import scanners from other modules and compose them into a `ScanJob`. To do this, add a `@scanjob` decorated function to your source file (it will be used in preference to `@scanner` decorated functions).

A `ScanJob` can also include `transcripts` or any other option that you can pass to `scout scan` (e.g. `model`). For example:

``` {.python filename="scanning.py"}
from inspect_scout import ScanJob, scanjob

@scanjob
def job() -> ScanJob:
    return ScanJob(
        scanners=[ctf_environment(), java_tool_usages()],
        transcripts="./logs",
        model="openai/gpt-5"
    )
```

You can then use the same command to run the job (`scout scan` will prefer a `@scanjob` defined in a file to individual scanners):

``` bash
scout scan scanning.py
```

You can also specify a scan job using YAML or JSON. For example, the following is equivalent to the example above:

``` {.yaml filename="scan.yaml"}
scanners:
  - name: deception
    file: scanner.py
  - name: java_tool_usages
    file: scanner.py

transcripts: logs
filter: task_set='cybench'

model: openai/gpt-5
```

Which can be executed with:

``` bash
scout scan scan.yaml
```

