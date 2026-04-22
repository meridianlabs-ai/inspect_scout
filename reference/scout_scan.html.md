# scout_scan – Inspect Scout

Scan transcripts and read results.

Pass a FILE which is either a Python script that contains @scanner or @scanjob decorated functions or a config file (YAML or JSON) that adheres to the [ScanJobConfig](../reference/scanning.html.md#scanjobconfig) schema.

#### Usage

``` text
scout scan [OPTIONS] COMMAND [ARGS]...
```

#### Subcommands

|  |  |
|----|----|
| [complete](#scout-scan-complete) | Complete a scan which is incomplete due to errors (errors are not retried). |
| [list](#scout-scan-list) | List the scans within the scans dir. |
| [resume](#scout-scan-resume) | Resume a scan which is incomplete due to interruption or errors (errors are retried). |
| [status](#scout-scan-status) | Print the status of a scan. |

## scout scan complete

Complete a scan which is incomplete due to errors (errors are not retried).

#### Usage

``` text
scout scan complete [OPTIONS] SCAN_LOCATION
```

#### Options

| Name | Type | Description | Default |
|----|----|----|----|
| `--display` | choice (`rich` \| `plain` \| `log` \| `none`) | Set the display type (defaults to ‘rich’) | `rich` |
| `--log-level` | choice (`debug` \| `trace` \| `http` \| `info` \| `warning` \| `error` \| `critical` \| `notset`) | Set the log level (defaults to ‘warning’) | `warning` |
| `--debug` | boolean | Wait to attach debugger | `False` |
| `--debug-port` | integer | Port number for debugger | `5678` |
| `--fail-on-error` | boolean | Re-raise exceptions instead of capturing them in results | `False` |
| `--help` | boolean | Show this message and exit. | `False` |

## scout scan list

List the scans within the scans dir.

#### Usage

``` text
scout scan list [OPTIONS] [SCANS_DIR]
```

#### Options

| Name | Type | Description | Default |
|----|----|----|----|
| `--display` | choice (`rich` \| `plain` \| `log` \| `none`) | Set the display type (defaults to ‘rich’) | `rich` |
| `--log-level` | choice (`debug` \| `trace` \| `http` \| `info` \| `warning` \| `error` \| `critical` \| `notset`) | Set the log level (defaults to ‘warning’) | `warning` |
| `--debug` | boolean | Wait to attach debugger | `False` |
| `--debug-port` | integer | Port number for debugger | `5678` |
| `--fail-on-error` | boolean | Re-raise exceptions instead of capturing them in results | `False` |
| `--help` | boolean | Show this message and exit. | `False` |

## scout scan resume

Resume a scan which is incomplete due to interruption or errors (errors are retried).

#### Usage

``` text
scout scan resume [OPTIONS] SCAN_LOCATION
```

#### Options

| Name | Type | Description | Default |
|----|----|----|----|
| `--display` | choice (`rich` \| `plain` \| `log` \| `none`) | Set the display type (defaults to ‘rich’) | `rich` |
| `--log-level` | choice (`debug` \| `trace` \| `http` \| `info` \| `warning` \| `error` \| `critical` \| `notset`) | Set the log level (defaults to ‘warning’) | `warning` |
| `--debug` | boolean | Wait to attach debugger | `False` |
| `--debug-port` | integer | Port number for debugger | `5678` |
| `--fail-on-error` | boolean | Re-raise exceptions instead of capturing them in results | `False` |
| `--help` | boolean | Show this message and exit. | `False` |

## scout scan status

Print the status of a scan.

#### Usage

``` text
scout scan status [OPTIONS] SCAN_LOCATION
```

#### Options

| Name | Type | Description | Default |
|----|----|----|----|
| `--display` | choice (`rich` \| `plain` \| `log` \| `none`) | Set the display type (defaults to ‘rich’) | `rich` |
| `--log-level` | choice (`debug` \| `trace` \| `http` \| `info` \| `warning` \| `error` \| `critical` \| `notset`) | Set the log level (defaults to ‘warning’) | `warning` |
| `--debug` | boolean | Wait to attach debugger | `False` |
| `--debug-port` | integer | Port number for debugger | `5678` |
| `--fail-on-error` | boolean | Re-raise exceptions instead of capturing them in results | `False` |
| `--help` | boolean | Show this message and exit. | `False` |
