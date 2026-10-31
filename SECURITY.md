# Security Policy

## Reporting a vulnerability

Email **security@meridianlabs.ai**. The address is monitored by Meridian Research Labs, which maintains Inspect Scout. Please do not open a public issue, discussion, or pull request for a suspected vulnerability.

Include as much of the following as you can:

- The version of `inspect_scout` and `inspect_ai` you tested, your Python version and operating system
- A description of the problem and what an attacker could do with it
- Steps to reproduce it, ideally a small script, scanner, or transcript
- Any logs, stack traces, or output that help show the behavior

## What to expect

- We will acknowledge your email within 3 business days.
- We will tell you within 10 business days whether we consider it a vulnerability and what we plan to do.
- We aim to release a fix within 30 days of the report. If a fix will take longer, we will tell you why.

We will keep you updated as we work on a fix, and we will let you know before we publish anything.

We do not run a bug bounty program and cannot pay for reports.

## Supported versions

We only fix security issues in the most recent release of `inspect_scout` on PyPI. We do not backport fixes to older versions. If you are running an older version, upgrade before reporting.

## Scope

Scout reads transcripts that contain model output, and scanners are Python programs. Running an untrusted scanner is equivalent to running untrusted code. The sections below describe what we treat as a vulnerability and what we do not.

### In scope

- Code execution or file access triggered by reading or viewing a transcript, eval log, transcript database, or scan results, in the Scout viewer or through Scout's Python API or CLI
- API keys, tokens, or other secrets written to scan results, logs, or error messages
- Path traversal, unauthenticated access, or other flaws in the Scout viewer or its server
- Model output that the viewer renders as active content (links, media, markup) when content trust is turned off
- Flaws in our release process, packaging, or CI that would let someone publish or modify a release

### Out of scope

- Loading a scanner, loader, or scan job from an untrusted source runs that code. Treat these the same way you would treat any other Python you did not write.
- Vulnerabilities in `inspect_ai` should be reported under [its security policy](https://github.com/UKGovernmentBEIS/inspect_ai/blob/main/SECURITY.md).
- Vulnerabilities in other third-party dependencies should be reported to that project. Tell us if `inspect_scout` needs a change in response, such as a version pin.
- Reports produced by a security scanner, or written mainly by an automated tool or a language model, with no working proof of concept. We will close these without a detailed response.

## Disclosure

We publish fixes as a GitHub security advisory on this repository and request a CVE where one applies. We will credit you by name unless you ask us not to.

Please keep the details private until the advisory is published.
