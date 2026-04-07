# scout db

Manage the local transcript database.

Scout transcript database management.

#### Usage

``` text
scout db [OPTIONS] COMMAND [ARGS]...
```

#### Subcommands

|  |  |
|----|----|
| [index](#scout-db-index) | Create or rebuild the index for a transcript database. |
| [schema](#scout-db-schema) | Print the transcript database schema. |
| [validate](#scout-db-validate) | Validate a transcript database schema. |

## scout db index

Create or rebuild the index for a transcript database.

This scans all parquet data files and creates a manifest index containing metadata for fast queries. Any existing index files are replaced.

#### Usage

``` text
scout db index [OPTIONS] DATABASE_LOCATION
```

#### Options

| Name     | Type    | Description                 | Default |
|----------|---------|-----------------------------|---------|
| `--help` | boolean | Show this message and exit. | `False` |

## scout db schema

Print the transcript database schema.

Outputs the schema in various formats for use when creating transcript databases outside of the Python API.

Examples: scout db schema \# Avro schema to stdout

    scout db schema --format pyarrow    # PyArrow schema

    scout db schema -o transcript.avsc  # Save to file

#### Usage

``` text
scout db schema [OPTIONS]
```

#### Options

| Name | Type | Description | Default |
|----|----|----|----|
| `--format` | choice (`avro` \| `pyarrow` \| `json` \| `pandas`) | Output format (default: avro). | `avro` |
| `--output`, `-o` | path | Write to file instead of stdout. | None |
| `--help` | boolean | Show this message and exit. | `False` |

## scout db validate

Validate a transcript database schema.

Checks that the database has the required fields and correct types.

Examples: scout db validate ./my_transcript_db

#### Usage

``` text
scout db validate [OPTIONS] DATABASE_LOCATION
```

#### Options

| Name     | Type    | Description                 | Default |
|----------|---------|-----------------------------|---------|
| `--help` | boolean | Show this message and exit. | `False` |
