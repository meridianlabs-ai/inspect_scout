# Contributing to Inspect Scout

Thanks for contributing to Inspect Scout — this guide covers local setup, the checks CI runs, and how commits map to releases.

<!-- BEGIN shared text from meridianlabs-ai/actions policy/CONTRIBUTING.md. Change it there, not here. -->
## How contributions work

There are two paths:

- **Qualified contributors**: maintainers and individuals recorded (by
  account id) in [`.github/qualified.yml`](.github/qualified.yml) — may open
  PRs directly.

- **Everyone else**: start from an issue a maintainer has labeled `accepted`
  before writing code, and reference it from your PR (`Fixes #NNN`). This
  applies regardless of your contribution history here, and regardless of
  who filed the issue — what matters is that a maintainer has accepted it.
  PRs that aren't linked to an accepted issue may be closed; if a linked
  issue is later accepted, reopen the PR.
  **Exception:** trivial documentation fixes (typos, broken links — docs
  files only, under 25 changed lines) are always welcome directly.

Whatever your path, check for an existing open PR addressing the same
problem before opening yours: duplicates are closed in favor of the earlier
PR unless a maintainer has asked for an alternative.

Issues a maintainer has labeled `deferred` are decisions not to prioritize
that work right now. PRs against a deferred issue are closed —
comment on the issue with new evidence or demand if you think it should be
revisited.

**Why:** like most open-source projects, we now receive a large volume of
unrequested, often agent-generated PRs. Reviewing a PR is time-consuming;
agreeing on a direction in an issue first is much easier. This policy spends
our review time on work we've agreed we want and spares you writing code we
can't merge.
<!-- END shared text from meridianlabs-ai/actions policy/CONTRIBUTING.md -->

## Development setup

Install [uv](https://docs.astral.sh/uv/) 0.13.4 or later, then clone the repository and create the environment:

```bash
git clone https://github.com/meridianlabs-ai/inspect_scout
cd inspect_scout
uv sync --locked --extra dev
```

`uv sync --locked` creates `.venv` with the exact versions in `uv.lock`, the `[dev]` extra included, and installs Scout editable. It fails if `uv.lock` is out of date with `pyproject.toml`. Run Python commands from the environment: `uv run <command>`, `.venv/bin/<command>`, or `source .venv/bin/activate`. `uv sync --locked` without `--extra dev` removes the dev tools again.

### Dependencies

[DEPENDENCIES.md](https://github.com/meridianlabs-ai/actions/blob/main/DEPENDENCIES.md) in meridianlabs-ai/actions tells how the Inspect repositories install and change dependencies. It covers the lock file, the cooldown, the canaries, inspect_ai `main`, and the procedures to add or update a dependency. Follow it. It is the same for every Inspect repository, so this file does not repeat it.

For this repository:

- inspect_scout needs unreleased inspect_ai changes. `[tool.uv.sources]` in `pyproject.toml` points `inspect-ai` at inspect_ai `main`.
- The 6-hour packages are in `[tool.uv.exclude-newer-package]` in `pyproject.toml`.

### Frontend (TypeScript viewer)

The web UI lives in a git submodule at `src/inspect_scout/_view/ts-mono` (Turborepo + pnpm) and uses Git LFS for binary assets. **This is only needed if you plan to work on the frontend** — Python-only contributors can skip it. You also need it to fix schema drift (see [Regenerating schema and types](#regenerating-schema-and-types)).

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

Shared types flow **Python (Pydantic models) → `openapi.json` → `generated.ts`**. These artifacts are generated, never hand-edited, and CI fails if they drift from source. After changing any Python model that crosses this boundary, regenerate and commit both artifacts. CI regenerates against inspect_ai main's latest commit, so move to it first:

```bash
uv sync --upgrade-package inspect-ai --extra dev
.venv/bin/python scripts/export_openapi_schema.py     # Python → openapi.json
cd src/inspect_scout/_view/ts-mono/apps/scout && pnpm types:generate   # openapi.json → generated.ts
```

Commit the updated `src/inspect_scout/_view/openapi.json` and `apps/scout/src/types/generated.ts`. CI also verifies the submodule pointer is a commit on `ts-mono`'s `main`, so merge the submodule PR before updating the pointer.

`check-schema-and-types` can also fail on a PR that changed no models. That happens when inspect_ai `main` changes a type that the schema includes. The same steps fix it, in a separate pair of PRs. [.agents/skills/sync-upstream-types/SKILL.md](.agents/skills/sync-upstream-types/SKILL.md) gives the full procedure. The check has no exemption, so the contributor who finds the drift fixes it.

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

A bug report needs a crisp minimal repro that **demonstrates** the bug: a real affected input, or steps that reproduce it. Show the repro rather than asserting the cause. That lets a maintainer confirm the bug and accept the issue.

## Bug-fix pull requests

If you are a maintainer or a qualified contributor and your bug-fix PR links no issue, the PR must include the repro that a bug report needs (see above). Without it, review is deferred until you add it.
