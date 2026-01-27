
::: {.callout-note}
The validation features described below are available only in the development version of Inspect Scout. Install the development version from GitHub with:

```python
pip install git+https://github.com/meridianlabs-ai/inspect_scout
```
:::

## Overview

When developing scanners, it's often desirable to create a feedback loop based on human labeling of transcripts that indicate expected scanner results. You can do this by creating a validation set and applying it during your scan:

![](images/validation-flow.jpg)

The *validation set* is the set of labeled transcripts that are compared against scan results. Validation sets are typically associated with the domain of a particular scanner type (e.g. "evaluation awareness", "refusal", etc.) so you will likely develop many of them for use with different scanners.

Apply a validation set by passing it to `scan()`. For example:

``` python
from inspect_scout import scan, transcripts_from

from my_scanners import eval_awareness

scan(
    scanners=[eval_awareness()],
    transcripts=transcripts_from("./logs"),
    validation="eval-awareness.csv"
)
```

Or from the command line:

``` bash
scout scan eval_awareness.py -V eval-awarness.csv
```

Validation sets are stored in CSV, YAML, JSON, or JSONL text files, however you don't need to edit them in their raw format. The next section describes recommended workflows for editing and managing validation sets.

## Validation Sets

The easiest way to work with validation data is to use [Scout View](index.qmd#scout-view), which provides inline editing of validation cases as well as various tools for editing and refining validation sets.

### Transcript View

When viewing any transcript, you can activate the validation case editor by clicking the button at the top right of the content view:

![](images/validation-panel-transcripts.png){.border}

A validation case maps a transcript to an expected target result. In the example above we indicate that this transcript does have evidence of evaluation awareness which should be detected by scanners.

### Results View

Sometimes its more convenient to apply validation labels in the context of scan results. There is also a validation editor available in every result view:

![](images/validation-panel-transcripts.png){.border}

It's often very natural to create cases this way as reviewing scan results often leads to judgments about whether the scanner is working as intended.

### Validation Pane

The **Validation** pane provides a top level view of all validation sets as well as various tools for managing them:

![](images/validation-pane.png){.border}

Use the validation pane to review and edit validation cases, manage [splits](#validation-splits), or copy and move validation cases between validation sets.

### Validation Files {#validation-files}

While you don't often need to edit validation files directly, you can do so if necessary since they are ordinary CSV for YAML files. For example, here's a validation set in CSV format:

``` {.default filename="eval-awareness.csv"}
id,target
Fg3KBpgFr6RSsEWmHBUqeo,true
VFkCH7gXWpJYUYonvfHxrG,false
SiEXpECj7U9nNAvM3H7JqB,true
```

If you are editing validation files directly you will need a way to discover trancript IDs. Use the **Copy** button in the transcript view to copy the UUID of the transcript you are viewing:

![](images/transcript-uuid-copy.png){.border}

See the [File Formats](#file-formats) section below for complete details on validation set files.

## Scanning

### Adding Validation

You'll typically create a distinct validation set (with potentially multiple splits) for each scanner, and then pass the validation sets to `scan()` as a dict mapping scanner to set:

``` {.python filename="scanning.py"}
from inspect_scout import scan, transcripts_from

scan(
    scanners=[ctf_environment(), eval_awareness()],
    transcripts=transcripts_from("./logs"),
    validation={
        "ctf_environment": "ctf-environment.csv",
        "eval_awareness": "eval-awareness.csv"
    }
)
```

If you have only only a single scanner you can pass the validation set without the mapping:

``` {.python filename="scanning.py"}
scan(
    scanners=[ctf_environment()],
    transcripts=transcripts_from("./logs"),
    validation="ctf-environment.csv"
)
```

You can also specify validation sets on the command line. If the above scans were defined in a `@scanjob` you could add a validation set from the CLI using the `-V` option as follows:

``` bash
# single validation set
scout scan scanning.py -V ctf-environment.csv

# multiple validation sets
scout scan scanning.py \
    -V ctf_environment:ctf-environment.csv \
    -V eval_awareness:eval-awareness.csv
```

### Validation Results

Validation results are reported in the scan status/summary UI:

![](images/validation-results-cli.png)

The validation metric reported in the task summary is the _balanced accurary_, which is good overall metric especially for unbalanced datasets (which is often the case for validation sets). Other metrics (precision, recall, and f1) are available in Scout View.

#### Scout View

Scout View will also show validation results alongside scanner values (sorting validated scans to the top for easy review):

![](images/validation.png){.border}


Validation results are reported using four standard classification metrics:

| Metric | Description |
|--------|-------------|
| **Accuracy** | Balanced accuracy: average of recall and specificity. Accounts for class imbalance better than raw accuracy. |
| **Precision** | When the scanner flags something, how often is it correct? High precision means few false alarms. |
| **Recall** | Of all items that should be flagged, how many did the scanner find? High recall means few missed cases. |
| **F1** | Harmonic mean of precision and recall. Useful when you need to balance both concerns. |

: {tbl-colwidths="[20,80]"}

In practice, there's often a tradeoff between precision and recall. A conservative scanner may have high precision but miss cases (low recall), while an aggressive scanner catches more cases (high recall) but with more false positives (lower precision). The right balance depends on your use case. Here are some resources that cover this in more depth:

- [Precision and Recall](https://en.wikipedia.org/wiki/Precision_and_recall) (Wikipedia) — Comprehensive overview of precision, recall, F1, and related metrics.
- [Classification Metrics](https://developers.google.com/machine-learning/crash-course/classification/precision-and-recall) (Google ML Crash Course) — Interactive tutorial on precision, recall, and the tradeoffs between them.
