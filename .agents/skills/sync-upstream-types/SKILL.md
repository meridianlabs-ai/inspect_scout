---
name: sync-upstream-types
description: Sync this repo's generated schema and types with inspect_ai main after inspect_ai changes a shared model. Use when check-schema-and-types fails on a PR that did not change the Python models, or when the schema drift check fails on a clean origin/main checkout.
---

# Sync generated types with inspect_ai main

CI regenerates `openapi.json` against inspect_ai `main`'s latest commit
(`.github/actions/uv-sync` runs `uv lock --upgrade-package inspect-ai`). When
inspect_ai changes a model that this repo's schema includes,
`check-schema-and-types` fails on every open PR until the regenerated
artifacts land on `main`. This skill makes that sync as one ts-mono +
inspect_scout PR pair. [land-ts-mono](../land-ts-mono/SKILL.md) then lands the
pair.

Whoever hits the drift does the sync. Do not skip `check-schema-and-types`,
make it optional, or merge with it red. This holds for every contributor,
whatever part of the code their own PR changes.

## 1. Recognize upstream drift

It is upstream drift when the check fails at "Check schema is up to date" and
the diff in the job log changes only types that come from inspect_ai, not
types your PR touched. For example, inspect_ai added `"excluded"` and
`"zeroed"` to the score reason enum:

```
-                  "scoring_failed"
+                  "scoring_failed",
+                  "excluded",
+                  "zeroed"
```

Other signs: the same failure shows on unrelated open PRs, or on the latest
`Build` run on `main`. The CI log's "Move inspect-ai to inspect_ai main" step
prints the inspect_ai commit it used (`Updated inspect-ai ... -> ...`).

If your PR also changed a model that feeds the schema, do not use this skill.
Regenerate in your own PR with `land-ts-mono`; that regeneration also picks
up the upstream change.

Before you start, look for an open sync pair in both repos (titles as in
step 5), and use it if it exists:

```bash
gh pr list -R meridianlabs-ai/inspect_scout --state open --search "regenerate in:title"
gh pr list -R meridianlabs-ai/ts-mono --state open --search "regenerate scout types in:title"
```

## 2. Check ts-mono's inspect-common types first

Scout's `generated.ts` has its own copy of the inspect_ai types that its
schema includes. The scout app also uses the same types from
`@tsmono/inspect-common` (`packages/inspect-common/src/types/generated.ts`),
and `apps/scout/src/query/schemaCompatibility.typecheck.ts` asserts that some
of them are identical. inspect_ai regenerates the inspect-common file with
its own `land-ts-mono`. Check that ts-mono `origin/main` already has the
upstream change, using a value from the diff in step 1. Run all commands in
this skill from the repo root unless a step says otherwise:

```bash
git submodule update --init
git -C src/inspect_scout/_view/ts-mono fetch origin
git -C src/inspect_scout/_view/ts-mono grep -n '"zeroed"' origin/main -- packages/inspect-common/src/types/generated.ts
```

If it does not, the inspect_ai side has not synced yet. Find the inspect_ai
ts-mono PR for that change, or open one with inspect_ai's `land-ts-mono`, and
land it first. Otherwise the two copies differ, and `pnpm check` can fail.

## 3. Prepare branches and environments

Cut both branches from `origin/main`, as in `land-ts-mono` step 1:

```bash
git fetch origin
git switch -c <branch> origin/main
git submodule update --init
git lfs pull                                   # dist/ is in Git LFS
cd src/inspect_scout/_view/ts-mono
git fetch origin
git switch -c <branch> origin/main             # same name as this repo's branch
pnpm install --frozen-lockfile
cd -
```

Install the inspect_ai that `check-schema-and-types` uses. This skill
assumes that `[tool.uv.sources]` in `pyproject.toml` points `inspect-ai` at
inspect_ai git `main`. If that changes, install what
`.github/actions/uv-sync` installs.

```bash
uv sync --upgrade-package inspect-ai --extra dev
git checkout -- uv.lock
```

The sync installs main's latest commit and also rewrites `uv.lock`. Do not
commit that `uv.lock` change; CI also restores it. From then on, run Python
through `.venv/bin/python` or `uv run --no-sync`. A plain `uv run` syncs the
venv back to the locked commit. Keep the repo's cooldown and
[DEPENDENCIES.md](https://github.com/meridianlabs-ai/actions/blob/main/DEPENDENCIES.md).
Never add `--no-config` or `--exclude-newer false`.

Record the installed version. Its `+g<sha>` suffix names the inspect_ai
commit. Compare it with the commit in the CI log:

```bash
.venv/bin/python -c "import importlib.metadata as m; print(m.version('inspect-ai'))"
```

## 4. Regenerate and check

```bash
.venv/bin/python scripts/export_openapi_schema.py    # writes openapi.json, then runs pnpm --filter scout types:generate
```

Read both diffs. Only the upstream change may appear, and only in these two
files (CI's "Ensure regeneration produced no other changes" step enforces
this):

```bash
git diff -- src/inspect_scout/_view/openapi.json
git -C src/inspect_scout/_view/ts-mono diff
```

`check_openapi_drift.py` compares the committed schema (`HEAD`) with the
working tree, so it fails until you commit `openapi.json`. Do what CI does:
commit `openapi.json` (step 5), regenerate again, and then run the check. It
must exit 0, and `git status` must show no new changes:

```bash
.venv/bin/python scripts/export_openapi_schema.py
uv run --no-sync python .github/scripts/check_openapi_drift.py
```

Then, from `src/inspect_scout/_view/ts-mono`, run one at a time:

```bash
pnpm check    # lint, format, typecheck; the same gate as js-dist-validation
pnpm test
pnpm build --force
```

Do not skip `pnpm build`. The ts-mono branch starts at ts-mono `origin/main`,
which is often ahead of this repo's gitlink. The build writes the viewer into
`src/inspect_scout/_view/dist`, so the bundle picks up every frontend commit
between the old gitlink and `origin/main`. `js-dist-validation` fails unless
you commit that rebuilt `dist/`. Use `--force`: the copy into `dist/` runs
in the scout vite build, and a turbo cache hit restores only
`apps/scout/dist` and skips that copy. Check that the build log shows
`[vite] Copied dist`. Back at the repo root, list the commits that
the bump picks up, for the PR body:

```bash
git -C src/inspect_scout/_view/ts-mono log --oneline "$(git rev-parse HEAD:src/inspect_scout/_view/ts-mono)"..origin/main
git status --short -- src/inspect_scout/_view/dist
```

## 5. Land with land-ts-mono

Land the pair with `land-ts-mono` from its step 3. Its rules for the merge
order and auto-merge apply. This skill adds only these points:

- Phase 1 (`land-ts-mono` step 3). The ts-mono PR has
  `apps/scout/src/types/generated.ts`. This repo's PR has `openapi.json`, the
  gitlink at the ts-mono branch head, and `dist/` if it changed. A rebuilt
  bundle has new hashed file names, so stage it with
  `git add -A src/inspect_scout/_view/dist` to record the deleted and the new
  files. Do not commit `uv.lock`. Use titles that step 1's search finds, for example
  `chore: regenerate scout types for inspect_ai main` (ts-mono) and
  `chore: regenerate schema and types for inspect_ai main` (this repo).
  In the PR body, list the ts-mono commits that the bump picks up.
- The expected phase 1 result is all green except `submodule-on-main`. That
  job is inside the `Build` workflow, so read job-level status
  (`gh run view <run-id> --json jobs`).
- inspect_ai `main` can move while the pair is open. If
  `check-schema-and-types` shows a new upstream diff, run the `uv sync` and
  `git checkout -- uv.lock` from step 3 again, then repeat step 4 on both
  branches.
- Phase 2 (`land-ts-mono` step 4). ts-mono `origin/main` can move past your
  merge before the gitlink bump. Run `pnpm build --force` again at the new gitlink
  and commit any `dist/` change with it, for the same reason as in step 4.

Other open PRs stay red until they get the fix from `main`. A re-run of the
failed job does not help, because a re-run tests the same merge commit. Merge
`origin/main` into the branch, or use the PR's "Update branch" button.
