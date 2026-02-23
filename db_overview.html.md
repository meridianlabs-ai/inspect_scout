# Transcripts Database


## Overview

Scout can analyze transcripts from any source (e.g. evals, agent traces,
RL rollouts, etc.) so long as the transcripts have been organized into a
transcripts database. Transcript databases use
[Parquet](https://parquet.apache.org) files for storage and can be
located in the local filesystem or remote systems like S3.

This documentation covers how to create transcript databases. If you
just want to read existing transcript databases see the general article
on [Transcripts](transcripts.qmd),

## Creating a Database

There are several sources you can use for building a transcript
database:

1.  Inspect evaluation logs.
2.  LLM observability systems (e.g. Arize Phoenix, LangSmith, Logfire).
3.  Traces directly captured from agent execution.
4.  Any other source using the import API.

Transcript databases have very few required fields (minimally just
`transcript_id` and `messages`) but there are other fields that identify
the source of the transcript that you’ll likely want to populate. You
can also include arbitrary other columns in the database (`metadata`)
which can be used for transcript filtering.

These articles cover transcript databases in more depth:

1.  [Database Schema](db_schema.qmd) — Documents the required and
    optional fields as well as data formats for transcript messages and
    events.

2.  [Capturing Transcripts](db_capturing.qmd) — Describes how to capture
    transcripts from running LLM code using the `@observe` decorator /
    context-manager.

3.  [Importing Transcripts](db_importing.qmd) — Covers building a
    database from Inspect Logs, Arize Phoenix, LangSmith, Logfire,
    Claude Code, and custom sources using the import API.

## Publishing Transcripts

If you want to publish transcripts for use by others, it’s important to
take precautions to ensure that the transcripts are not unintentionally
read by web crawlers. Some techniques for doing this include using
protected S3 buckets or permissioned HuggingFace datasets, as well as
encryping the Parquet files that hold the transcripts. The article on
[Publishing Transcripts](db_publishing.qmd) includes additional details
on how to do this.
