# AGENTS.md

## Repository Structure
- **Python package** (`src/inspect_scout/`) - Core library for analyzing LLM evaluation transcripts. Provides a CLI, programmatic API, and FastAPI server. Handles transcript databases, scanners, validation, and results.
- **React frontend** (`src/inspect_scout/_view/ts-mono/`) - TypeScript monorepo (Turborepo + pnpm workspaces) for the web UI, embedded as a git submodule. See its own [CLAUDE.md](src/inspect_scout/_view/ts-mono/CLAUDE.md) and [submodule guide](src/inspect_scout/_view/ts-mono/docs/submodule-guide.md).

Development setup (editable install, inspect_ai tracked from `main`, frontend/Git LFS setup) is in [CONTRIBUTING.md](CONTRIBUTING.md).

## Principles

- Shortcuts become someone else's problem; hacks compound into debt
- Patterns get copied—establish good ones
- Flag issues; ask before fixing
- Strict typing required
  - Python: modern syntax (`X | None`, `dict[str, Any]`)
  - TypeScript: no `any`, no type assertions
- Error handling: appropriate exceptions with context
- Respect existing patterns
- Before committing, run the appropriate checks for code you touched (lint, typecheck, test)

### Testing
- Test observable behavior, not internal implementation details
- Do not test things that are enforced by the type system
- Test through the narrowest public API that covers the behavior
- Be efficient; avoid duplicate coverage
- Prefer data/table driven tests for maintainability
- Tests must be isolated; no shared mutable state or order dependencies
- Tests must be deterministic; control randomness with seeds
- Prefer real objects over mocks when possible
- Mark async tests with `@pytest.mark.asyncio`—pytest-asyncio runs in strict mode, so an unmarked `async def` test fails with "async def functions are not natively supported"

### Common Pitfalls
- Stay within scope—don't make unrequested changes
- Never edit generated files—`openapi.json` and `generated.ts` are generated; modify source and regenerate
- During development, run only implicated tests; run the full suite when the work is complete
- Git LFS tracks `src/inspect_scout/_view/dist/**` (built frontend assets)—without `git lfs install`, a checkout leaves pointer stubs, not real files

## Pull Requests

- Title PRs as Conventional Commits (`<type>: <description>`)—we squash-merge, so the PR title becomes the commit message that drives releases; `pr-title-lint` enforces it
- Describe the user-facing outcome in the title, not the mechanism: "fix: scan hangs when transcripts are on S3", not "fix: use AsyncFilesystem in transcript loader". The title becomes a release-notes line—a user scanning the notes should recognize their problem or their feature. PRs with no user-facing outcome (refactoring, tooling, docs) describe the change itself
- `feat:`/`fix:` are for user-facing changes only: they headline the release notes and bump the version. `perf:`/`revert:` also appear in the notes (no bump); `docs:`, `refactor:`, `chore:`, `build:`, `ci:`, `test:`, `style:` are hidden
- Body lines starting with `<type>:` are parsed as extra changelog entries—don't begin description lines with a conventional-commit prefix unless that's intended
- Never edit `CHANGELOG.md`, version numbers, or `.release-please-manifest.json`—Release Please owns them
- After opening a PR, watch its checks until they complete (`gh pr checks <number> --watch`); investigate and fix any failures
- See [CONTRIBUTING.md](CONTRIBUTING.md) for full guidelines

### Agent review disclosure

PRs prepared by AI coding agents must disclose agent involvement in the description, including an `### Agent review` section summarizing pre-PR review passes: what model/tool reviewed, whether the review ran in a fresh context and/or used a different model from the author, how many passes, and the findings—issues found, which were fixed, and which were dismissed with a one-line reason each. Multiple passes, each in a fresh context, often catch issues a single pass misses—prefer that for non-trivial changes. If no review pass was run, say so explicitly. Never report a review that didn't happen—a fabricated or content-free claim ("reviewed, looks good") is worse than disclosing none. Example:

```
### Agent review
- Reviewer: Claude Opus 5 via /code-review (fresh context), 2 passes
- Findings: 3 — 2 fixed, 1 dismissed (flagged a missing None check that is
  guarded upstream)
```

### Submodule pointer

Never change the ts-mono submodule gitlink (`src/inspect_scout/_view/ts-mono`) unless the task is about the frontend. After any merge or rebase, if `git status` shows the submodule modified, check `git diff HEAD -- src/inspect_scout/_view/ts-mono` to tell two look-alike states apart:

- **No gitlink change** (the diff is empty; only the local submodule worktree is stale): run `git submodule update`.
- **Gitlink changed** (the recorded pointer was bumped incidentally): reset it and commit: `git checkout origin/main -- src/inspect_scout/_view/ts-mono`. `git submodule update` will NOT fix this—it syncs the working tree to the already-recorded pointer, not the reverse. Never `git add` the submodule path in this state—that stages the wrong pointer.

When a change legitimately requires a coordinated ts-mono update (e.g. regenerated types), follow [.claude/skills/land-ts-mono/SKILL.md](.claude/skills/land-ts-mono/SKILL.md).

## Documentation

Consult documentation when you need deeper context on how subsystems work.

### User Docs
`/docs/` - Quarto-based documentation site: https://meridianlabs-ai.github.io/inspect_scout/
- Scanners, transcripts, validation, results, projects, workflows, DB schema

### Design Documents
Architecture and design decisions in `/design/`.

- [Transcript data pipeline](design/data-pipeline.md)
- [Job vs infrastructure exceptions](design/exception_handling.md)
- [FastAPI endpoint async convention](design/fastapi-async.md)
- [Async generator semantics](design/generator-iterator.md)
- [Multi-process concurrency](design/mp.md)
- [Validation data structures](design/validation.md)
- [React Query patterns](src/inspect_scout/_view/ts-mono/apps/scout/design/react-query.md)
- [Frontend specific testing](src/inspect_scout/_view/ts-mono/apps/scout/design/front-end-testing.md)

## Python

Directory: `src/inspect_scout/`

### Scripts
| Command | Description |
|---------|-------------|
| `make check` | Run all checks (lint, format, typecheck) |
| `make test` | Run all tests |
| `pytest` | Run all tests |
| `pytest tests/path/to/test.py::test_name -v` | Run single test |
| `pytest -n 0 ...` | Run without xdist workers (debugging, `pdb`, readable output) |
| `ruff format` | Format code |
| `ruff check --fix` | Lint and auto-fix |
| `mypy src examples tests` | Type check |

Notes:
- `pytest` runs under xdist by default (`-n logical --dist worksteal` in `pyproject.toml`)
- Tests marked `slow`, `api`, or `flaky` are skipped by default; enable with `--runslow`, `--runapi`, `--runflaky`. The default suite needs no API keys

### Style
- **Formatting**: Follow Google style convention. Use ruff for formatting
- **Imports**: Use isort order (enforced by ruff)
- **Types**: All functions must have type annotations, including in tests.
- **Typed returns**: When a function returns multiple values, prefer a `NamedTuple` (or small dataclass) over a bare tuple. Adjacent same-typed slots (and `bool`/`int` adjacency) make positional mistakes invisible to the type checker; named fields keep construction sites keyword-checked and give call sites self-documenting attribute access
- **Naming**: Use snake_case for variables, functions, methods; PascalCase for classes
- **Docstrings**: Google-style docstrings required for public APIs
- **Comments at call sites**: Don't describe what a function does at the call site—the function's name and docstring already document that, and the comment will drift if the function evolves. A call-site comment is appropriate only when the *reason this caller specifically invokes it* isn't obvious from surrounding context (e.g. an unusual ordering constraint, a workaround for a known bug in this code path). When in doubt, write the docstring and leave the call site uncommented
- **Comment length**: When a comment is needed to explain rationale or context, be concise. Preserve the important information but don't be pedantic or verbose; don't replay a commit or PR description into a comment
- **Error Handling**: Use appropriate exception types; include context in error messages
- **Testing**: Write tests with pytest; maintain high coverage

### Async and Concurrency
- **Concurrent tasks**: Use `tg_collect()` from `inspect_ai._util._async` instead of `asyncio.gather()` for running concurrent async tasks
- **FastAPI endpoints must not block the event loop.** An `async def` endpoint runs on the loop thread—one sync blocking call (file I/O, subprocess, sync DB access) stalls every request. An endpoint that never awaits but does blocking I/O should be a plain `def` (FastAPI runs it in a threadpool). An endpoint that awaits *and* blocks must offload the blocker with `anyio.to_thread.run_sync`. Decision tree: [design/fastapi-async.md](design/fastapi-async.md)
- **Job errors don't crash the scan.** Failures in scanner/parse work (user scanner code, model API errors, malformed data) are caught at the containment boundary (`_parse_function`/`_scan_function`) and returned as `Error` results; only infrastructure failures propagate. Don't add handling that lets a job exception escape, and don't swallow infrastructure exceptions. See [design/exception_handling.md](design/exception_handling.md)
- **File paths**: code that handles paths must support remote URLs (`s3://`) as well as plain local paths—use `filesystem()` from `inspect_ai._util.file`, not `os`/`pathlib`, on user-supplied paths

### Common Pitfalls
- Use the venv for all Python commands: either reference `.venv/bin/` directly or run `source .venv/bin/activate`
- **Never use `uv sync` or `uv run`**—developers often have local editable installs (e.g., `pip install -e` for inspect_ai) that uv silently removes


## TypeScript

Directory: `src/inspect_scout/_view/ts-mono/` (run all commands from here)

See the frontend's own [CLAUDE.md](src/inspect_scout/_view/ts-mono/CLAUDE.md) for full details.

### Setup
```bash
corepack enable  # once
pnpm install
```

### Scripts
| Command | Description |
|---------|-------------|
| `pnpm check` | Run all checks (lint, format, typecheck) via Turborepo |
| `pnpm dev` | Start dev server (user typically has this running—don't start) |
| `pnpm watch` | Watch mode—defined per app (`apps/scout`, `apps/inspect`), not at the root (user typically has this running—don't start) |
| `pnpm build` | Production build |
| `pnpm test` | Run unit/integration tests |
| `pnpm lint` | Lint all packages |
| `pnpm typecheck` | Type-check all packages |
| `pnpm format` | Format code |

### Style
- Strict mode enabled; no `any`, no type assertions
- ESLint + Prettier

### Architecture
- Panels that initiate an async query own its `AsyncData` lifecycle and render loading/error states at that boundary; components rendered only after data is ready take required data props rather than reading query/loading state themselves

### Common Pitfalls
- Use pnpm, not npm—this project uses pnpm exclusively
- Hook tests don't need JSX—use `.test.ts` not `.test.tsx`; see `useMapAsyncData.test.ts`
- Run `pnpm check` to type check, lint, and otherwise check your code quality
- Run `pnpm build` before committing (not just `pnpm check`)—we ship the built .js code


## Type Sharing (Python → TypeScript)

Pipeline: Pydantic models → openapi.json → generated.ts

After Python API changes:
1. `.venv/bin/python scripts/export_openapi_schema.py`—regenerates `src/inspect_scout/_view/openapi.json`
2. In the submodule's `apps/scout`: `pnpm types:generate`—regenerates `apps/scout/src/types/generated.ts` (`pnpm build` does NOT regenerate types)
3. Commit both: `openapi.json` in this repo, `generated.ts` in the submodule. Landing a submodule change requires the coordinated flow in [.claude/skills/land-ts-mono/SKILL.md](.claude/skills/land-ts-mono/SKILL.md)

CI validates sync.
