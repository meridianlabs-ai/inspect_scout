# scout_view – Inspect Scout

View scan results.

#### Usage

``` text
scout view [OPTIONS] [PROJECT_DIR]
```

#### Options

| Name | Type | Description | Default |
|----|----|----|----|
| `-T`, `--transcripts` | text | Location of transcripts to view. | None |
| `--scans` | text | Location of scan results to view. | None |
| `--mode` | choice (`default` \| `scans`) | View display mode. | `default` |
| `--host` | text | Tcp/Ip host for view server. | `127.0.0.1` |
| `--port` | integer | Port to use for the view server. | `7576` |
| `--browser` / `--no-browser` | boolean | Open in web browser. | None |
| `--root-path` | text | ASGI root_path for serving behind a reverse proxy. | \``| |`–display`| choice (`rich`&#x7C;`plain`&#x7C;`log`&#x7C;`none`) | Set the display type (defaults to 'rich') |`rich`| |`–log-level`| choice (`debug`&#x7C;`trace`&#x7C;`http`&#x7C;`info`&#x7C;`warning`&#x7C;`error`&#x7C;`critical`&#x7C;`notset`) | Set the log level (defaults to 'warning') |`warning`| |`–debug`| boolean | Wait to attach debugger |`False`| |`–debug-port`| integer | Port number for debugger |`5678`| |`–fail-on-error`| boolean | Re-raise exceptions instead of capturing them in results |`False`| |`–help`| boolean | Show this message and exit. |`False\` |
