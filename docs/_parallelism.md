
The Scout scanning pipeline is optimized for parallel reading and scanning as well as minimal memory consumption. There are a few options you can use to tune parallelism:

| Option | Description |
|---------------------------|---------------------------------------------|
| `--max-transcripts` | Sets the number of scan workers: `--max-transcripts` x the number of scanners (defaults to 25). A worker scans one whole transcript or one loader item (for example one message), so the items of one transcript can scan in parallel. Any scanner can use any free worker. You can set this higher if your model API endpoint can handle larger numbers of concurrent requests. |
| `--max-connections` | The maximum number of concurrent requests to each model (defaults to `--max-transcripts`). This limits model calls only. At `--max-connections 1`, scanner code can still run in parallel with other scanner code. |
| `--max-processes` | The maximum number of processes to use for parsing and scanning (defaults to 4). |
: {tbl-colwidths=[35,65]}

With more than one process, the items of a transcript scan in the process that read that transcript. So when a scan has few transcripts, some processes can have no work.