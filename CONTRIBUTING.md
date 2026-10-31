# Contributing to Inspect Scout

Thanks for contributing to Inspect Scout — this guide covers local setup, the checks CI runs, and how commits map to releases.

## Development setup

Install [uv](https://docs.astral.sh/uv/) 0.13.4 or later, then clone the repository and create the environment:

```bash
git clone https://github.com/meridianlabs-ai/inspect_scout
cd inspect_scout
uv sync --extra dev
```

`uv sync` creates `.venv` with the exact versions in `uv.lock`, the `[dev]` extra included, and installs Scout editable. Run Python commands from it: `uv run <command>`, `.venv/bin/<command>`, or `source .venv/bin/activate`. `uv sync` without `--extra dev` removes the dev tools again.

### Dependencies and the cooldown

`uv.lock` pins every Python dependency. CI's type-check, test, build and schema jobs install from it with `uv sync --locked`, which fails when `uv.lock` is out of date with `pyproject.toml`. When you change dependencies in `pyproject.toml`, run `uv lock` and commit both files.

`pyproject.toml` sets `exclude-newer = "7 days"` under `[tool.uv]`, so `uv lock`, `uv sync` and `uv pip` only pick releases that have been on PyPI for at least seven days. A compromised release is usually found and removed within that time, before it reaches `uv.lock`, CI or your machine. A few packages wait 6 hours instead, so a new release can be adopted the day it ships: `inspect-ai`, `inspect-swe`, the `anthropic`, `openai` and `google-genai` SDKs, and `certifi`, the CA bundle. They are listed in `[tool.uv.exclude-newer-package]`. Dependabot's `uv` entry in `.github/dependabot.yml` repeats the cooldown and the list, and `tests/test_dependency_cooldown.py` checks that they match.

Dependabot proposes `uv.lock` updates daily, once a release has cleared its cooldown. To adopt a release sooner, run `uv lock --upgrade-package <package>` and commit `uv.lock`. A release still inside its cooldown can't be locked; wait for it rather than overriding `exclude-newer`.

Testing against the newest release of every dependency happens in the nightly canary in [meridianlabs-ai/canaries](https://github.com/meridianlabs-ai/canaries), so Scout's own CI doesn't need to.

### inspect_ai main

Development and CI track inspect_ai's `main` branch. `[tool.uv.sources]` in `pyproject.toml` points `inspect-ai` at its git repository, and `uv.lock` records the commit. Only uv reads `[tool.uv.sources]`: the published package requires the `inspect-ai>=` floor in `[project]`.

- To move to inspect_ai's latest `main` commit, run `uv lock --upgrade-package inspect-ai` and commit `uv.lock`.
- On the release PR, `.github/workflows/release-pin-deps.yml` removes the git source, locks the newest inspect-ai release that has cleared its cooldown, and raises the floor to it, so the release is tested against the inspect_ai it will require. After the release PR merges, the same workflow opens a PR titled "build: track inspect_ai main again after the release". Merge it to go back to tracking `main`.

To work against a local inspect_ai checkout, install it over the locked one:

```bash
uv sync --extra dev
uv pip install -e ../inspect_ai
```

Then run commands with `.venv/bin/<command>` or `uv run --no-sync <command>`. A plain `uv run` or `uv sync` reinstalls the locked inspect_ai.

### Frontend (TypeScript viewer)

The web UI lives in a git submodule at `src/inspect_scout/_view/ts-mono` (Turborepo + pnpm) and uses Git LFS for binary assets. **This is only needed if you plan to work on the frontend** — Python-only contributors can skip it.

1. [Install Git LFS](https://git-lfs.com/) and run `git lfs install`.
2. Initialize the submodule and install dependencies:

   ```bash
   git submodule update --init
   cd src/inspect_scout/_view/ts-mono
   pnpm install
   ```

3. Recommended: `git config submodule.recurse true` so `git pull` keeps the submodule working tree in sync.

See the [submodule guide](src/inspect_scout/_view/ts-mono/docs/submodule-guide.md) for full workflows.

## Checks and tests

Before committing, run the checks for the code you touched.

**Python** (from the repo root):

```bash
make check   # ruff check --fix, ruff format, and mypy
make test    # pytest
```

**Frontend** (from `src/inspect_scout/_view/ts-mono`):

```bash
pnpm check   # lint, format, and typecheck via Turborepo
pnpm test    # unit/integration tests
pnpm build   # production build — run before committing; we ship the built JS
```

### Regenerating schema and types

Shared types flow **Python (Pydantic models) → `openapi.json` → `generated.ts`**. These artifacts are generated, never hand-edited, and CI fails if they drift from source. After changing any Python model that crosses this boundary, regenerate and commit both artifacts:

```bash
.venv/bin/python scripts/export_openapi_schema.py     # Python → openapi.json
cd src/inspect_scout/_view/ts-mono/apps/scout && pnpm types:generate   # openapi.json → generated.ts
```

Commit the updated `src/inspect_scout/_view/openapi.json` and `apps/scout/src/types/generated.ts`. CI also verifies the submodule pointer is a commit on `ts-mono`'s `main`, so merge the submodule PR before updating the pointer.

## Commit messages and releases

We use [Conventional Commits](https://www.conventionalcommits.org/). Because we
squash-merge, **the PR title becomes the commit message** — so the title is what
matters. Format it as `<type>: <description>`.

Releases are automated with [Release Please](https://github.com/googleapis/release-please):
**don't edit `CHANGELOG.md` or bump the version by hand.** Release Please reads the
merged commit types, opens a release PR that updates the changelog and version, and
merging that PR tags the release; the publishes (PyPI and the npm viewer lib) then
run once a maintainer approves each deployment.

Choose the type deliberately — `feat:` and `fix:` drive the version bump and
headline the release notes:

| Type | Effect |
| --- | --- |
| `feat:` | a user-facing feature — bumps the patch version (pre-1.0 policy) |
| `fix:` | a user-facing bug fix — bumps the patch version |
| `perf:`, `revert:` | appear in the release notes (no bump on their own) |
| `docs:`, `refactor:`, `chore:`, `build:`, `ci:`, `test:`, `style:` | hidden from the release notes |

Anything that isn't a user-facing feature or fix should avoid `feat:`/`fix:` so it
stays out of the headline sections.

## Reporting issues

Found a bug or have a feature request? Please open an issue on the [GitHub issue tracker](https://github.com/meridianlabs-ai/inspect_scout/issues).

## Bug-fix pull requests

A bug-fix PR should either link the issue it resolves or include a crisp minimal repro that **demonstrates** the bug: a real affected input, or steps that reproduce it, alongside the root cause. Show the repro rather than asserting the cause. That lets a reviewer confirm the diagnosis instead of reverse-engineering it, and keeps the PR from stalling. Without an issue or a demonstrated repro, review is deferred until you add one.
