#!/usr/bin/env python3
"""Extract user corrections from Claude Code conversation logs.

Scans JSONL conversation files for messages where the user corrected Claude.
Useful for identifying patterns to add to AGENTS.md Common Pitfalls sections.

Usage:
    .venv/bin/python scripts/extract_corrections.py [project_path]

If project_path not provided, uses the current working directory.

Sample output:
    just run related tests - not all of them
    ---
    wait. did you just manually add it to openapi.json? that misses the whole point
    ---
    omg. get it together. this project uses pnpm and not npm
    ---
    do not ever use uv run in this repo. just use .venv directly
    ---
    what the heck, you reversed yourself on _ZipMemberBytes again
    ---
    === Total unique corrections found: 288 ===

Prompt for analyzing output:
    Analyze the following user corrections from Claude Code conversations.
    Categorize them into themes (e.g., "wrong test scope", "wrong package manager",
    "edited generated files", "inconsistent decisions"). For each theme with 3+
    occurrences, draft a concise pitfall entry for AGENTS.md in this format:

    - **[Short title]**—[one-line explanation of what to do/avoid]

    Focus on actionable guidance. Skip corrections that are project-specific
    edge cases or one-offs.
"""

import json
import re
import sys
from pathlib import Path


def get_project_dir(project_path: str | None = None) -> Path:
    """Get the Claude Code project directory for conversation logs."""
    if project_path is None:
        project_path = str(Path.cwd().resolve())

    # Convert path to Claude's naming convention (slashes and underscores become hyphens)
    safe_name = project_path.replace("/", "-").replace("_", "-")
    if safe_name.startswith("-"):
        safe_name = safe_name[1:]

    return Path.home() / ".claude/projects" / f"-{safe_name}"


# Patterns suggesting user corrections
CORRECTION_PATTERNS = [
    r"^\s*no[,.\s!]",
    r"^don't",
    r"\bwrong\b",
    r"\bshould\b",
    r"\binstead\b",
    r"^\s*stop\b",
    r"\bnot\b",
    r"\bthat's not\b",
    r"\bactually\b",
    r"^\s*wait\b",
    r"\bundo\b",
    r"\brevert\b",
    r"shouldn't",
    r"\bconfused\b",
    r"\bmisunderstand\b",
    r"\bdisagree\b",
    r"\breversed\b",
    r"\b\?\?\?\b",
    r"what the heck",
    r"I don't think",
    r"I don't want",
    r"double check",
    r"check again",
    r"think.*hard",
    r"just run",
    r"do NOT",
]


def extract_corrections(project_dir: Path) -> list[str]:
    """Extract correction messages from conversation logs."""
    pattern = re.compile("|".join(CORRECTION_PATTERNS), re.IGNORECASE)
    corrections: list[str] = []

    files = [f for f in project_dir.glob("*.jsonl") if f.stat().st_size > 1000]

    for jsonl_file in sorted(files):
        with open(jsonl_file) as f:
            for line in f:
                try:
                    msg = json.loads(line)
                    message = msg.get("message", {})
                    if isinstance(message, dict) and message.get("role") == "user":
                        content = message.get("content", "")

                        # Handle both string and list content
                        texts: list[str] = []
                        if isinstance(content, str):
                            texts = [content]
                        elif isinstance(content, list):
                            for block in content:
                                if (
                                    isinstance(block, dict)
                                    and block.get("type") == "text"
                                ):
                                    texts.append(block.get("text", ""))

                        for text in texts:
                            # Skip system/command messages
                            if (
                                text.startswith("<")
                                or "command-" in text
                                or "[Request interrupted" in text
                            ):
                                continue
                            if pattern.search(text) and 15 < len(text) < 500:
                                corrections.append(text.strip())
                except json.JSONDecodeError:
                    pass

    return corrections


def main() -> None:
    project_path = sys.argv[1] if len(sys.argv) > 1 else None
    project_dir = get_project_dir(project_path)

    if not project_dir.exists():
        print(f"Project directory not found: {project_dir}")
        sys.exit(1)

    corrections = extract_corrections(project_dir)

    # Dedupe while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for c in corrections:
        if c not in seen:
            seen.add(c)
            unique.append(c)

    for c in unique:
        print(c)
        print("---")

    print(f"\n=== Total unique corrections found: {len(unique)} ===")


if __name__ == "__main__":
    main()
