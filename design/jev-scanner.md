# Jev scanner

`jev_scanner()` scans transcripts with TypeSafe Jev, a classification model that returns probabilities for fixed options (yes/no, one of up to 255 labels, a 2-10 level rubric) and no free text. `cascade_scanner()` escalates uncertain cases to `llm_scanner()`.

## Shared pipeline

`llm_scanner` and `jev_scanner` share `_llm_scanner/_pipeline.py`: resolving the scanner input (transcript vs. streaming handle), extracting messages (timelines, events, or raw messages), segmenting to a token budget, scanning segments with bounded concurrency, and aggregating with `aggregate_results`. Each scanner supplies only a per-segment `scan_segment(messages_str) -> Result`. Fixes to timelines, compaction, or streaming therefore apply to both.

## Jev as an Inspect provider

Jev is reached through an Inspect `ModelAPI` registered as `typesafe` (`_jev_scanner/_provider.py`), not a bespoke HTTP client. `generate()` accepts exactly one user message whose text is a JSON request `{state, questions, long_context}` and returns the answers in `ModelOutput.metadata["answers"]`; anything else raises, because Jev cannot generate text.

Routing Jev through Inspect gives it, without private APIs or custom code:

- usage accounting (`scan_model_usage`, `scan_total_tokens`, scan summaries)
- the generate cache (`cache=`), which matters because Jev is not exactly deterministic
- retries (`should_retry`: rate limits, 5xx, connection errors, timeouts; the SDK's own retries are disabled)
- connection limits (the scan's `max_connections`, by default `max_transcripts`)
- `count_tokens` (Jev counts ~1.2-1.4x Inspect's default estimate, so the provider uses 2.3 characters/token)
- model roles and base URL overrides

`jev_scanner` refuses models whose provider lacks the `jev_provider` marker before sending anything, so a misconfigured generative model is never billed for Jev requests. The SDK client is created lazily per event loop, since scan workers are spawned processes that pickle scanners (an HTTP client cannot be pickled or shared across loops). The provider registers when `inspect_scout` is imported, so it resolves in every worker. `typesafe-sdk` is imported lazily, with an install hint.

## Result shapes

`jev_scanner` results have exactly the value shapes of `llm_scanner`, so reducers, validation, and `value_to_float` behave the same: booleans are `bool` (probability at or above `threshold`), single labels are letters with the label text in `answer`, multi-labels are lists of label texts, numeric answers are the expected rubric score, and structured answers follow `structured_result()`'s value/label/metadata rules. Answer types needing free text are rejected when the scanner is built.

The explanation is assembled from the answer, its probability, the matching criterion, and the cited messages (`[M#]`), and passed through `extract_refs` so the viewer links citations. Because reducers merge metadata shallowly, a multi-segment result keeps the reducer's metadata, adds per-segment metadata under `segments`, and aggregates `p` (max), evidence (merged), and tokens/seconds (summed). `value_to_float` is applied after reduction so reducers like `any` see raw booleans (an intentional difference from `llm_scanner`, whose per-segment conversion defeats `any`).

Oversized segments: Jev's `max_tokens_exceeded` error is mapped by the provider to `JevInputTooLongError` (from the error body or message), and the scanner re-segments once at half the budget.

## Evidence

Citations come from choice questions over the segment's message labels (windows of 250 plus `NONE`, at most 1,000 labels per request so the options fit the 8k reserve). Labels are the segment's consecutive header run, and references are built only from cited labels, so imitated headers or `[M#]` in label/criteria text cannot create citations. A window answering `NONE` cites nothing. For booleans they are asked with the answer (the target, "that the answer is yes", is fixed); for other answer types a follow-up request names the chosen answer, since Jev answers all questions in a request independently. `references="all"` repeats the question with found messages and their immediate neighbours removed (neighbours are usually the same occurrence: a tool call's output, or the announcing turn), stopping at `NONE`, a probability below 0.3, or 8 citations.

## Cascade

Cascade options are typed dictionaries (`JevOptions`, `LlmOptions`, `EscalateRules`). Escalation rules are JSON data (`p_between`, `positive`, `labels`, `confidence_below`) so cascades survive YAML jobs and `scout scan resume`. The LLM stage's question carries Jev's `criteria`/`rubric`, so both stages answer on the same scale. The LLM stage's model is resolved before the Jev call, so a missing key fails before Jev tokens are spent. `llm=False` flags would-be escalations with `needs_review` instead of calling an LLM.

## Redaction

`redact_secrets()` (`_scanner/redact.py`) is a `MessagesPreprocessor` transform that removes keys and credentials (and, with `"all"`, emails) from message text, reasoning, tool-call arguments (string leaves, plus values of secret-named keys, so argument structure survives), tool errors, and server-side tool use, preserving message ids. Values that look like code or variable references (`os.environ[...]`, `${VAR}`) are left intact. `jev_scanner` applies it by default (`redact="keys"`); `cascade_scanner` applies the same preprocessor to both stages.
