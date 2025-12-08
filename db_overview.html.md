# Transcripts Database


## Overview

Scout can analyze transcripts from any source (e.g. Agent traces, RL
rollouts, etc.) so long as the transcripts have been organized into a
transcripts database. Transcript databases use
[Parquet](https://parquet.apache.org) files for storage and can be
located in the local filesystem or remote systems like S3.

The purpose of transcript databases is to provide a common baseline
format for scanners to read from. You might use transcript databases as
your cannonical storage for transcripts, or you might alternatively
store them in another system entirely (e.g. a Postgress database) and
extract them into a Scout database for a given analysis project.

This documentation covers how to create transcript databases, import
your transcripts into them, and publish them for use by others. If you
just want to read existing transcript databases see the general article
on [Transcripts](transcripts.qmd),

## Creating a Database

If you have some existing source of transcript data it is
straightforward to import it into a Scout database. Transcript databases
have very few required fields (minimally just `transcript_id` and
`messages`) but there are other fields that identify the source of the
transcript that you’ll likely want to populate. You can also include
arbitrary other columns in the database (`metadata`) which can be used
for transcript filtering.

Use the `transcripts_db()` async context manager to open a connection to
a database (which can be stored in a local file path or remote file
system like S3):

``` python
from inspect_scout import transcripts_db

async with transcripts_db("s3://my-transcripts") as db:
    # TODO: insert transcripts into db
```

To popualte the database you’ll need to:

1.  Understand the [Database Schema](db_schema.qmd) and decide how you
    want to map your data source into it; and

2.  Pick a method for [Importing Transcripts](db_importing.qmd) and
    implement the logic for inserting your data.

## Publishing Transcripts

If you want to publish transcripts for use by others, it’s important to
take precautions to ensure that the transcripts are not unintentionally
read by web crawlers. Some techniques for doing this include using
protected S3 buckets or permissioned HuggingFace datasets, as well as
encryping the Parquet files that hold the transcripts. The article on
[Publishing Transcripts](db_publishing.qmd) includes additional details
on how to do this.
