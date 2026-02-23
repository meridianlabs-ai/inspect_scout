# Scanners


## Overview

Scanners are the main unit of processing in Inspect Scout and can target
a wide variety of content types. In this article we’ll cover using the
high-level scanners provided with Scout ([LLM Scanner](#llm-scanner) and
[Grep Scanner](#grep-scanner)) as well as the basics of creating custom
scanners.

## Using Scanners

We’ll cover defining various types of scanners below—first though let’s
describe how scanners are used in Scout.

Scanners are defined either in Python source file or Python package, and
are passed as the first argument to `scout scan`. For example:

``` bash
scout scan scanner.py -T ./logs --model openai/gpt-5
```

Or from Python:

``` python
from inspect_scout import scan
from scanner import my_scanner

results = scan(
    scanners=[my_scanner()],
    transcripts="./logs",
    model="openai/gpt-5" 
)
```

Once a scan is complete you can view its results by running `scout view`
or by computing on the data frame(s) returned in `results`.

Note that if you want run multiple scanners at once you can either pass
a list of scanners to the `scan()` function or define a scan job (see
[Scan Jobs](#scan-jobs) below for details).

## LLM Scanner

For many applications you can use the high-level `llm_scanner()`, which
uses a model for transcript analysis and can be customized with many
options. For example:

**scanner.py**

``` python
from inspect_scout import Scanner, Transcript, llm_scanner, scanner

@scanner(messages="all")
def ctf_environment() -> Scanner[Transcript]:
    return llm_scanner(
        question="In the transcript above do you detect "
        "instances of environment misconfiguration "
        "preventing the agent from completing it's task?",
        answer="boolean"
    )
```

The `llm_scanner()` supports a wide variety of model answer types
including boolean, number, string, classification (single or multi), and
structured JSON output. For additional details, see the [LLM
Scanner](llm_scanner.qmd) article.

## Grep Scanner

Using an LLM to search transcripts is often required for more nuanced
judgements, but if you are just looking for text patterns, you can also
use the `grep_scanner()`. For example, here we search assistant messages
for references to phrases that might indicate secrets:

``` python
from inspect_scout import Transcript, grep_scanner, scanner

@scanner(messages=["assistant"])
def secrets() -> Scanner[Transcript]:
    return grep_scanner(["password", "secret", "token"])
```

For additional details on using this scanner, see the [Grep
Scanner](grep_scanner.qmd) article.

## Custom Scanners

If the higher level LLM and Grep scanners don’t meet your requirements,
you can write a custom scanners with whatever behavior you need. For
example, the following illustrates the implementation of a basic LLM
scanner (click on the numbers at right for further explanation):

**scanner.py**

``` python
from inspect_scout import (
    Result, Scanner, Transcript, scanner, message_numbering
)

from inspect_ai.model import get_model
import re

@scanner(messages="all")
def ctf_environment() -> Scanner[Transcript]:
    
    async def scan(transcript: Transcript) -> Result:

        # setup message numbering
        messages_as_str, extract_refs = message_numbering()

        # call model
        output = await get_model().generate(
            "Here is a transcript of an LLM agent " +
            "solving a cybersecurity challenge:\n\n" +
            "===================================" +
            await messages_as_str(transcript.messages) +
            "===================================\n\n" +
            "In the transcript above do you detect any " +
            "instances of environment misconfiguration " +
            "preventing the agent from completing its " +
            "task? If no, simply respond with 'No'. " +
            "If yes, respond with 'Yes' followed by an " +
            "explanation."
        )

        # extract the first word
        match = re.match(r"^\w+", output.completion.strip())

        # return result
        if match:
            answer = match.group(0)
            explanation = output.completion
            return Result(
                value=answer.lower() == "yes",
                answer=answer,
                explanation=explanation,
                references=extract_refs(explanation)
            )
        else:
            return Result(value=False, explanation=output.completion)

    return scan
```

Line 8  
Scanners are decorated with `@scanner` so they can specify the exact
subset of content they need to read. In this case only messages (and not
events) will be read from the log, decreasing load time.

Line 17  
Scanners frequently use models to perform scanning. Calling
`get_model()` utilizes the default model for the scan job (which can be
specified in the top level call to scan).

Lines 20-22  
Convert the message history into a string for presentation to the model.
The `messages_as_str()` function takes a `Transcript | list[Messages]`
and will by default remove system messages from the message list. See
`MessagesPreprocessor` for other available options.

Lines 38-43  
As with scorers, results also include additional context (here the
extracted answer, full model completion, and message references).

For more details on creating custom scanners, including scanning
individual messages or events, handling compaction and context overflow,
and computing metrics, see the article on [Custom
Scanners](custom_scanner.qmd).

## Scan Jobs

You may want to import scanners from other modules and compose them into
a `ScanJob`. To do this, add a `@scanjob` decorated function to your
source file (it will be used in preference to `@scanner` decorated
functions).

A `ScanJob` can also include `transcripts` or any other option that you
can pass to `scout scan` (e.g. `model`). For example:

**scanning.py**

``` python
from inspect_scout import ScanJob, scanjob

@scanjob
def job() -> ScanJob:
    return ScanJob(
        scanners=[ctf_environment(), java_tool_usages()],
        transcripts="./logs",
        model="openai/gpt-5"
    )
```

You can then use the same command to run the job (`scout scan` will
prefer a `@scanjob` defined in a file to individual scanners):

``` bash
scout scan scanning.py
```

You can also specify a scan job using YAML or JSON. For example, the
following is equivalent to the example above:

**scan.yaml**

``` yaml
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

## Learning More

To learn more about using and developing scanners, see the following
articles:

- [LLM Scanner](llm_scanner.qmd): High level scanner for using models to
  read transcripts.

- [Grep Scanner](grep_scanner.qmd): High level scanner for pattern
  matching in transcripts.

- [Custom Scanners](custom_scanner.qmd): Comprehensive documentation on
  creating custom scanners.

- [Scanner Tools](scanner_tools.qmd): Create custom scanners with the
  same tools used under the hood by `llm_scanner()`.
