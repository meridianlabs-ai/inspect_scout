
The Scout scanning pipeline is optimized for parallel reading and scanning as well as minimal memory consumption. There are a few options you can use to tune parallelism:

| Option | Description |
|---------------------------|---------------------------------------------|
| `--max-transcripts` | The maximum number of transcripts to scan in parallel (defaults to 25). You can set this higher if your model API endpoint can handle larger numbers of concurrent requests. |
| `--max-connections` | The maximum number of concurrent requests to the model provider (defaults to `--max-transcripts`). It also bounds how many items yielded for one transcript (e.g. each message for a `ChatMessage` scanner) are scanned in parallel; set it to 1 to scan them one at a time in order. |
| `--max-processes` | The maximum number of processes to use for parsing and scanning (defaults to 4). |
: {tbl-colwidths=[35,65]}