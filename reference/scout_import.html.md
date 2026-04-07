# scout import

Import transcripts from external sources into the local database.

Import transcripts from a source.

#### Usage

``` text
scout import [OPTIONS] [SOURCE]
```

#### Options

| Name | Type | Description | Default |
|----|----|----|----|
| `-T`, `--transcripts` | text | Transcripts database directory. | `./transcripts` |
| `--limit` | integer | Maximum number of transcripts to import. | None |
| `--from` | text | Only import transcripts on or after this time (ISO 8601). | None |
| `--to` | text | Only import transcripts before this time (ISO 8601). | None |
| `-P` | text | Source parameter as name=value (repeatable). | None |
| `--sources` | boolean | List available sources and their parameters. | `False` |
| `--dry-run` | boolean | Fetch and display summary without writing. | `False` |
| `--overwrite` | boolean | Overwrite existing transcripts directory without prompting. | `False` |
| `--display` | choice (`rich` \| `plain` \| `log` \| `none`) | Set the display type (defaults to ‘rich’) | `rich` |
| `--log-level` | choice (`debug` \| `trace` \| `http` \| `info` \| `warning` \| `error` \| `critical` \| `notset`) | Set the log level (defaults to ‘warning’) | `warning` |
| `--debug` | boolean | Wait to attach debugger | `False` |
| `--debug-port` | integer | Port number for debugger | `5678` |
| `--fail-on-error` | boolean | Re-raise exceptions instead of capturing them in results | `False` |
| `--help` | boolean | Show this message and exit. | `False` |
