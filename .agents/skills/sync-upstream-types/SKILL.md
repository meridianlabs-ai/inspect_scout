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

Before you start, look for an open sync pair in both repos, and use it if it
exists:

```bash
gh pr list -R meridianlabs-ai/inspect_scout --state open --search "regenerate in:title"
gh pr list -R meridianlabs-ai/ts-mono --state open --search "scout types in:title"
```

## 2. Check ts-mono's inspect-common types first

Scout's `generated.ts` imports inspect-originated types from
`@tsmono/inspect-common` (`packages/inspect-common/src/types/generated.ts`).
inspect_ai regenerates that file with its own `land-ts-mono`. Check that
ts-mono `origin/main` already has the upstream change, using a value from the
diff in step 1:

```bash
git -C src/inspect_scout/_view/ts-mono fetch origin
git -C src/inspect_scout/_view/ts-mono grep -n '"zeroed"' origin/main -- packages/inspect-common/src/types/generated.ts
```

If it does not, the inspect_ai side has not synced yet. Find the inspect_ai
ts-mono PR for that change, or open one with inspect_ai's `land-ts-mono`, and
land it first. Then `pnpm check` here runs against the same inspect-common
types.

## 3. Prepare branches and environments

Cut both branches fresh from `origin/main`. Never commit on the submodule's
detached HEAD or on a stale local `main`.

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

Install the inspect_ai that `check-schema-and-types` uses. Read
`[tool.uv.sources]` in `pyproject.toml`:

- `inspect-ai` points at inspect_ai git `main`: run
  `uv sync --upgrade-package inspect-ai --extra dev`. This installs main's
  latest commit and also rewrites `uv.lock`. Do not commit that `uv.lock`
  change. Run `git checkout -- uv.lock` (CI does the same). After that, run
  Python through `.venv/bin/python` or `uv run --no-sync`. A plain `uv run`
  syncs the venv back to the locked commit.
- No git source (inspect-ai comes from PyPI): run
  `uv sync --locked --extra dev`. A new release reaches CI only through a
  `uv.lock` change, which is a dependency change under
  [DEPENDENCIES.md](https://github.com/meridianlabs-ai/actions/blob/main/DEPENDENCIES.md).

Keep the repo's cooldown. Never add `--no-config` or `--exclude-newer false`.

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
working tree. Before you commit, it prints the upstream diff and exits 1.
After you commit `openapi.json` (step 5), run it again. It must exit 0:

```bash
uv run --no-sync python .github/scripts/check_openapi_drift.py
```

Then, from `src/inspect_scout/_view/ts-mono`, run one at a time:

```bash
pnpm check    # lint, format, typecheck; the same gate as js-dist-validation
pnpm test
pnpm build
```

Do not skip `pnpm build`. The ts-mono branch starts at ts-mono `origin/main`,
which is often ahead of this repo's gitlink. The build writes the viewer into
`src/inspect_scout/_view/dist`, so the bundle picks up every frontend commit
between the old gitlink and `origin/main`. `js-dist-validation` fails unless
you commit that rebuilt `dist/`. List the commits that the bump picks up, for
the PR body:

```bash
git -C src/inspect_scout/_view/ts-mono log --oneline "$(git rev-parse HEAD:src/inspect_scout/_view/ts-mono)"..origin/main
git status --short -- src/inspect_scout/_view/dist
```

## 5. Land with land-ts-mono

Phase 1 is `land-ts-mono` step 3:

1. In the submodule, commit `apps/scout/src/types/generated.ts`, push the
   branch, and open the ts-mono PR.
2. In this repo, commit `openapi.json`, the gitlink at the ts-mono branch
   head, and `dist/` if it changed. Do not commit `uv.lock`. Push, and open
   the PR.
3. Cross-link the two PRs in their descriptions.

The expected result is all green on this repo's PR except
`submodule-on-main`. That job is inside the `Build` workflow, so read
job-level status (`gh run view <run-id> --json jobs`). inspect_ai `main` can
move while the pair is open. If `check-schema-and-types` shows a new upstream
diff, repeat step 4 on both branches.

Phase 2 is `land-ts-mono` step 4. After the ts-mono PR merges, its squash or
rebase gives a new SHA. Bump the gitlink to ts-mono `origin/main`, which may
have moved again. Then run `pnpm install --frozen-lockfile && pnpm build`,
commit the gitlink and any `dist/` change, push, and enable auto-merge on
this repo's PR.

Other open PRs stay red until they get the fix from `main`. A re-run of the
failed job does not help, because a re-run tests the same merge commit. Merge
`origin/main` into the branch, or use the PR's "Update branch" button.
