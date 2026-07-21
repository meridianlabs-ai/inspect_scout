# Contributing to Inspect Scout

Thanks for contributing to Inspect Scout — this guide covers local setup, the checks CI runs, and how commits map to releases.

## Development setup

Clone the repository and install it editable with the `[dev]` extras. Development tracks `inspect_ai` from `main`, so install that first (this is what CI does):

```bash
git clone https://github.com/meridianlabs-ai/inspect_scout
cd inspect_scout
pip install git+https://github.com/UKGovernmentBEIS/inspect_ai.git
pip install -e ".[dev]"
```

Run all Python commands from the project virtualenv (reference `.venv/bin/` directly or `source .venv/bin/activate`). Do **not** use `uv sync` or `uv run` — they can silently remove local editable installs.

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
cd src/inspect_scout/_view/ts-mono && pnpm build       # openapi.json → generated.ts
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
