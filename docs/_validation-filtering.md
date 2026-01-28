Your validation set will typically be only a subset of all of the transcripts you are scanning, and is intended to provide a rough heuristic on how prompt changes are impacting results. In some cases you will want to *only* evaluate transcript content that is included in the validation set. The `Transcript` class includes a filtering function to do this. For example:

``` python
from inspect_scout import scan, transcripts_from, validation_set

validation={
    "ctf_environment": "ctf-environment.csv",
    "eval_awareness": "eval-awareness.csv"
}

transcripts = transcripts_from("./logs")
transcripts = transcripts.for_validation(validation)

scan(
    scanners=[ctf_environment(), eval_awareness()],
    transcripts=transcripts,
    validation=validation
)
```