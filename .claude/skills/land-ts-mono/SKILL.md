---
name: land-ts-mono
description: Land a PR that requires a coordinated ts-mono submodule change. Use when the check-schema-and-types CI job fails, when a Python model change requires regenerating the OpenAPI spec / TypeScript types, or when any change touches the ts-mono submodule and needs to be landed.
---

# Landing coordinated ts-mono changes

A change in this repo sometimes requires a matching change in the ts-mono
submodule — most commonly because a Python model feeding the type-generation
pipeline changed, which regenerates a file *inside* the submodule. Landing
then requires a cross-repo dance: a ts-mono PR, a gitlink bump here, and a
specific merge order. This skill is the sanctioned procedure for changing the
submodule gitlink (see the submodule guide in repo facts for background).

## Repo facts

<!-- Porting this skill to another repo (e.g. inspect_ai): swap this
     section's values; the procedure below is repo-agnostic. -->

- Submodule: `src/inspect_scout/_view/ts-mono` → https://github.com/meridianlabs-ai/ts-mono (branch `main`)
- Regeneration command: `.venv/bin/python scripts/export_openapi_schema.py`
  (from repo root; requires `pnpm install` done in the submodule; it writes
  the schema then chains `pnpm --filter scout types:generate`)
- Regeneration runs against the **installed** inspect_ai, and CI regenerates
  against inspect_ai git `main` — so regenerate with inspect_ai at main (a
  lagging editable install bakes in false drift)
- Generated artifacts:
  - `src/inspect_scout/_view/openapi.json` (this repo)
  - `apps/scout/src/types/generated.ts` (inside the submodule)
- CI jobs (`.github/workflows/build.yaml`):
  - `check-schema-and-types` — artifacts must match the Python source (docstring-only drift tolerated) and each other (exactly)
  - `submodule-on-main` — the gitlink SHA must be reachable from ts-mono `main`
  - `js-dist-validation` — the checked-in viewer bundle `src/inspect_scout/_view/dist` must match `pnpm build` run at the pinned submodule commit (the scout app's vite build copies its output into this repo's `dist/`)
- ts-mono has merge commits **disabled** (squash or rebase only). Both of
  those rewrite the commit, so the merged change lands under a *new* SHA and
  the branch head the gitlink points at in phase 1 does not become reachable
  from ts-mono `main` — plan on the second gitlink bump in step 4.2. This
  holds even for a single-commit PR sitting directly on `main`: GitHub's
  "Rebase and merge" re-commits rather than fast-forwarding (measured on
  ts-mono#609, 1 commit / 0 behind — `d9fcc775` → `24b515da`, identical
  tree). A true fast-forward push straight to `main` would keep the SHA, but
  that is not a path the PR UI offers.
- Submodule checks before pushing: `pnpm typecheck` and `pnpm test` from the ts-mono root (turbo), not per-package tsc
- Pipeline internals: "Type Sharing" section of `CLAUDE.md`; submodule workflows: `src/inspect_scout/_view/ts-mono/docs/submodule-guide.md`
- Sibling consumer: `inspect_ai` (also embeds ts-mono, at `src/inspect_ai/_view/ts-mono`; its regen `python src/inspect_ai/_view/schema.py` produces `packages/inspect-common/src/types/generated.ts`). Types flow inspect_ai → scout: scout's `generated.ts` imports inspect-originated types from `@tsmono/inspect-common`, and nothing on the inspect_ai side duplicates scout's types — so scout Python changes rarely require a sibling sync (see step 2a).

## Recognize the situation

- `check-schema-and-types` is red on your PR, or
- you changed a Python model that flows into the pipeline (anything reachable
  from the `_view` API models — Transcript, ValidationCase, ScannerInput,
  LlmScannerParams, ScanOptions/ScanJobConfig, or anything they reference), or
- your change requires editing code in the submodule directly.

## Procedure

Your job is to reach the landed state from **whatever state you find** — you
may be starting fresh or resuming mid-flight (possibly in a new session).
First assess where things stand, then enter at the matching step:

| Observed state | Enter at |
|---|---|
| No ts-mono branch/PR yet | step 1 |
| Regeneration not done or stale | step 2 |
| ts-mono PR open; this repo's PR not yet gitlink-bumped/pushed | step 3 |
| Both PRs open; this repo's PR behind `main` or conflicted | update the branch (see pitfalls), then step 4 |
| Both PRs in phase-1 state (green / green-except-gate) | step 4 |
| ts-mono PR merged; gate still red | step 4.2 |

Resumption relies on the PR cross-links (step 3) to find the paired PR, and
any monitors/watches from a previous session are gone — re-arm them.

**Finding the paired ts-mono branch:** the submodule sits on a detached HEAD,
so the work branch isn't announced. The authoritative probes work whatever
the branch is named: `git -C <submodule> branch -a --contains HEAD` lists
every branch containing the gitlink commit, and the PR cross-links (step 3)
name the ts-mono PR's head branch. Branches are *usually* named the same as
this repo's branch (step 1's convention), which makes a good first guess —
but never a requirement. If nothing but `main`-ish refs contain HEAD, there's
no branch yet — that's the fresh-start case (step 1). Before committing in
the submodule, `git checkout <branch>` — a commit made on the detached HEAD
lands on no branch. A local branch may also lag its remote; trust
`origin/<branch>`, not the local ref.

### 1. Start submodule work from current main

In the submodule, `git fetch origin` and branch from `origin/main` — NOT the
local `main` ref, which lags arbitrarily far behind (submodules live on
detached HEADs; nothing routinely updates their local branches, and `fetch`
moves only `origin/main`). You must be current with ts-mono `origin/main`
before merging anyway, so get current before making changes. Name the new
branch after this repo's branch — a convention that makes the pairing obvious
at a glance (discovery doesn't depend on it; see "Finding the paired ts-mono
branch" above).

### 2. Make the change / regenerate

Sync this repo's branch with its `origin/main` (fetch first) before
regenerating — the schema that
lands is generated from the merged Python, so regenerating against a stale
branch bakes in a schema that drifts the moment you update the branch.

For type changes, run the regeneration command. It rewrites both generated
artifacts — one in this repo, one in the submodule. Docstring-only changes do
NOT require regeneration (CI tolerates `description` drift); only structural
changes do.

Run the submodule checks (see repo facts) before pushing. Expect fixture
fallout: adding a required field means test/e2e fixtures constructing
literals of that type need the new field.

### 2a. Sibling sync — rarely needed from this side

Types flow inspect_ai → scout, not the reverse: a scout Python change
regenerates only scout's own `generated.ts`, and nothing inspect_ai consumes
duplicates scout's types. So the cross-repo type-sync dance (which inspect_ai
must do when *its* shared types change) has no counterpart here for model
changes.

The exception is direct edits to shared ts-mono packages (`packages/*`):
those can break the inspect app or other consumers in the monorepo. Running
`pnpm typecheck` / `pnpm test` from the ts-mono root catches this — fix the
fallout in the same ts-mono PR. inspect_ai's own `dist-validation` reconciles
whenever it next bumps its gitlink; that's not your job here, but flag
breaking shared-package changes in the ts-mono PR description.

### 3. Two-phase landing — phase 1: branch-pinned, reviewable

1. Commit on the ts-mono branch, push it, open a ts-mono PR.
2. In this repo, commit the gitlink pointing at the ts-mono **branch head**
   (plus any regenerated files here) and push.
3. Cross-link the two PRs in each other's descriptions.

Result: this repo's PR is green **except** `submodule-on-main`. That one red
gate is the expected signal meaning "waiting on ts-mono merge". Do not try
to fix it yet. It stays red through the merge. It clears only after you bump
the gitlink to the merged SHA in step 4.2, so do not tell anyone the merge
alone will clear it. Note: `submodule-on-main` is a job inside the "Build"
workflow, so that whole workflow shows as failing in rollup views. Read
job-level status before concluding anything else broke.

**Why two-phase:** once ts-mono merges, its `main` depends on Python changes
that aren't merged yet, blocking anyone else who pulls ts-mono `main`. The
goal is to make that window as short as possible: get *everything else* green
on both PRs first, and only then merge ts-mono.

### 4. Phase 2: merge in order, quickly

Preconditions — ALL of these before anyone merges anything:

- ts-mono PR green and approved
- this repo's PR green except `submodule-on-main`
- this repo's PR **provisionally approved**: a reviewer has approved it with
  the sole remaining red being `submodule-on-main`

The provisional approval matters: it puts review latency *before* the
blocking window opens. Once ts-mono merges, the only remaining work should
be re-running one gate — not waiting on a reviewer.

Auto-merge: NEVER enable it on the ts-mono PR. Merging it opens the blocking
window, so it needs explicit approval and must not fire just because checks
pass. The Python PR is the opposite. Once ts-mono is merged, enable
auto-merge on it yourself (`gh pr merge --auto`) so it lands the moment the
gate clears.

1. Tell the user both PRs are ready, and ask for approval to merge the
   ts-mono PR. Merging it is the deliberate act that opens the blocking
   window. Do it only with the user's explicit approval, never on your own
   initiative. Start watching its merged state as soon as you ask (background
   poll, e.g. `gh pr view <n> --json state,mergeCommit`), because whoever
   merges it may not be you. React the moment it lands. The blocking window
   opens at merge, so don't wait for the user to come back and tell you.
2. Fetch in the submodule, then compare the gitlink SHA against ts-mono
   `origin/main`:
   - **SHA changed** (squash or rebase merge, which is anything the ts-mono
     PR UI can do): bump the gitlink to the merged `main` SHA. The bump picks
     up **every** ts-mono `main` change since the last bump, not just yours,
     so rebuild the viewer bundle at the new
     commit (`pnpm install --frozen-lockfile && pnpm build` in the
     submodule; the build copies output into this repo's
     `src/inspect_scout/_view/dist`) and commit the gitlink together with
     any resulting `dist/` changes (often none — type-only deltas build
     identically — but `js-dist-validation` fails if you skip the check and
     something did change). Push.
   - **SHA unchanged** (merge commit; branch head now reachable from main):
     just re-run the red `submodule-on-main` check. Requires the branch head
     itself to land on `main` — merge commits are disabled on ts-mono and
     rebase merge rewrites the commit, so expect this case not to arise.
3. Enable auto-merge on this repo's PR (`gh pr merge --auto`) and tell the
   user — the PR lands automatically the moment the gate clears. Watch until
   it actually merges; if auto-merge is unavailable (repo settings), watch CI
   and tell the user the instant it's mergeable instead.

## Pitfalls

- You need push access to the Python PR's head branch. GitHub's
  allow-maintainer-edits does NOT work for PRs from organization-owned
  forks — if the head lives in one you can't push to, recreate the PR from
  an in-repo branch (preserving the original description and crediting the
  author) and close the original with a link.
- Never leave the gitlink pointing at an unpushed or local-only ts-mono
  commit — push the ts-mono branch before committing the bump.
- After merging this repo's `origin/main` into your branch, check `git status` for
  the gitlink: a merge can silently revert your intentional bump.
- If `main` bumps the gitlink while your PR is open, GitHub reports a
  submodule conflict and stops running CI on the PR. Fix: merge `origin/main`
  into your branch; at the gitlink conflict, verify main's new pointer is an
  ancestor of your ts-mono branch head
  (`git -C <submodule> merge-base --is-ancestor <main-ptr> <yours>`) — it
  will be if you branched from current ts-mono main — then keep yours
  (`git add <submodule>`), commit, push. If it is NOT an ancestor, first
  merge ts-mono `origin/main` into your ts-mono branch and push, then point
  the gitlink at that. A gitlink-bumping main commit usually also rebuilds the
  checked-in viewer `dist/` — taking main's dist is correct when your ts-mono
  delta is types/tests only (type erasure leaves the build output identical);
  otherwise rebuild dist from your ts-mono branch.
- Regenerate only from a venv with this repo installed AND inspect_ai at
  main (CI regenerates against inspect_ai git main; an editable inspect_ai
  install that lags main produces false drift). Stale submodule
  `node_modules` breaks the TypeScript half — `pnpm install` in the submodule
  first.
- Don't trust the branch's committed schema just because its CI once passed —
  a later branch commit can change the Python models and leave
  `openapi.json` stale against the branch's *own* source. When
  resuming mid-flight, re-run the regeneration command and confirm it's a
  no-op before entering phase 2.
