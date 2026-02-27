# Frontend Separation Plan: TypeScript Monorepo

## Contents

1. [Problem Statement](#problem-statement)
2. [Requirements](#requirements)
3. [Design Proposal](#design-proposal)
   - [Overview](#overview)
4. [How Each Story Is Solved](#how-each-story-is-solved)
5. [Walkthrough: What's Different](#walkthrough-whats-different-for-a-coordinated-frontend--api-feature)
6. [Supporting Details](#supporting-details)
   - [TypeScript Monorepo Structure](#typescript-monorepo-structure)
   - [Vite Output Path Detection](#vite-output-path-detection)
   - [Type Generation Pipeline](#type-generation-pipeline)
7. [Implementation and Migration](#implementation-and-migration)

## Problem Statement

Currently, **TypeScript code is copied between `inspect_ai` and `inspect_scout`** — duplication and maintenance burden.

**Goal**: Eliminate the duplication by sharing TypeScript code between `inspect_ai` and `inspect_scout` in a monorepo. The frontend must continue to "just work" for all users — installing, developing, and releasing should require no additional steps or tooling beyond what's already familiar.

> [!TIP]
> Related problems (unminified builds, missing asset fingerprinting) are addressed separately in [minified-via-lfs.md](minified-via-lfs.md).

## Requirements

### Personas

| Persona | Description |
|---------|-------------|
| **PyPI user** | Installs from PyPI. No git, no Node.js. |
| **Git user** | Installs from a git ref or clones the repo. No Node.js. |
| **Python-only contributor** | Develops Python code. Has the dev environment but no Node.js. |
| **Frontend contributor** | Works across both the TS monorepo and the Python repo — just as they work across TypeScript and Python code today. Has Node.js and the Python dev environment. |
| **Python package maintainer** | Cuts releases and publishes to PyPI. |

### Stories

| # | Title | Description |
|---|-------|-------------|
| 1 | **PyPI user** can `scout view` after installing from PyPI | `pip install inspect-scout` provides a working frontend. No extra steps, no network fetch at install time, no Node.js required. |
| 2 | **Git user** can `scout view` after installing a git ref | `pip install git+https://...[@ref]` provides a working frontend. No extra steps beyond having network access. No Node.js required. |
| 3 | **Python-only contributor** can `scout view` after `pip install -e`'ing | `git clone && pip install -e ".[dev]"` provides a working frontend automatically. Python-only changes require no frontend awareness or Node.js. |
| 4 | **Frontend contributor** can develop and publish UI-only changes | Changes that don't require API modifications. The contributor works in the TS monorepo, builds, commits `dist/` to the Python repo, and pushes. Others can test the branch or the merged result without Node.js. |
| 5 | **Frontend contributor** can develop and publish coordinated API + UI changes | Changes that require new or modified Python API endpoints. The contributor updates the API, regenerates TypeScript types, develops the frontend against them, and publishes both sides. |
| 6 | **Git user** can test a prepared WIP branch | A git user can install a Python branch and get the matching in-progress frontend automatically, without needing Node.js. |
| 7 | **Python package maintainer** can publish a release that includes the correct frontend | When a maintainer cuts a release, the resulting wheel includes the correct frontend build. No manual steps beyond the normal release process. No Node.js required. |
| 8 | **Python repo CI** catches mismatched `openapi.json` | If a contributor changes the Python API without re-exporting the schema, CI fails the build with a specific error message. |
| 9 | **Python repo CI** catches mismatched `generated.ts` | If a contributor updates the schema without regenerating TypeScript types, CI fails the build with a specific error message. |
| 10 | **Python repo CI** catches mismatched `dist/` | If a contributor modifies the frontend without rebuilding dist, CI fails the build with a specific error message. |

## Design Proposal

### Overview

The TypeScript code for both `inspect_ai` and `inspect_scout` frontends lives in a **separate git repository** (the TS monorepo), managed with **pnpm workspaces** and **Turborepo**. Shared code (components, utilities, types) is factored into workspace packages consumed by both apps.

> [!NOTE]
> The design hinges on two things:
> 1. **Git submodules** — the Python repo references a specific TS monorepo commit, providing traceability without coupling the two repos
> 2. **Cross-repo build output** — `pnpm build` in the submodule writes directly into the Python repo's serving path, so committed `dist/` is always a product of a known source commit

The Python repo includes the TS monorepo as a **git submodule** at `src/inspect_scout/_view/ts-mono/`. The built `dist/` is committed to the Python repo, so non-frontend users never need Node.js — `git clone` and `pip install` deliver working frontend assets automatically. The "publish" step is the same as today: **build, commit, push.**

Vite automatically detects whether it's running inside a Python repo (submodule mode) or standalone, and outputs to the right place. See [Vite Output Path Detection](#vite-output-path-detection) for details.

## How Each Story Is Solved

Since `dist/` is committed to the Python repo, most stories work the same as today. The differences are in how the frontend contributor works with the submodule.

| Story | Summary | Details |
|-------|---------|---------|
| 1. PyPI user | Same as today | |
| 2. Git user | Same as today | |
| 3. Python-only contributor | Same as today | |
| **4. UI-only changes** | Init submodule, develop, build, commit dist | Init submodule, `pnpm install`, develop with `pnpm dev`. Build with `pnpm build` (outputs to Python repo's serving path). Commit `dist/` and submodule pointer to the Python repo. |
| **5. Coordinated API + UI changes** | Update API, regenerate types, develop, build, commit | Change Python API models, re-export `openapi.json`, regenerate TS types, develop frontend against new types. Build and commit `dist/` + submodule pointer to Python repo alongside the API changes. |
| 6. Git user tests WIP branch | Same as today | |
| 7. Python release | Same as today | |
| **8. CI catches mismatched `openapi.json`** | Re-export schema, diff | The `openapi-schema` job re-exports `openapi.json` from the Python API and diffs against the committed version. A mismatch fails with a specific error message and recovery instructions. |
| **9. CI catches mismatched `generated.ts`** | Regenerate types, diff | The `js-dist-validation` job regenerates `generated.ts` from the committed `openapi.json` and diffs against the committed version. A mismatch fails with a specific error message and recovery instructions. |
| **10. CI catches mismatched `dist/`** | Build, diff | The `js-dist-validation` job runs `pnpm build` from the submodule at its recorded pointer and diffs against the committed `dist/`. A mismatch fails with a specific error message and recovery instructions. |

## Walkthrough: What's Different for a Coordinated Frontend + API Feature

The overall workflow — clone, branch, develop, test, commit, merge, release — is unchanged. The only new steps for a frontend contributor are:

1. **Initialize the submodule once:** `git submodule update --init && cd src/inspect_scout/_view/ts-mono && pnpm install`
2. **Develop in the submodule:** work on a feature branch inside `src/inspect_scout/_view/ts-mono/`, using `pnpm dev` for hot reload
3. **Build into the Python repo:** `pnpm build` outputs to `src/inspect_scout/_view/dist/`
4. **Commit both:** `git add src/inspect_scout/_view/dist/ src/inspect_scout/_view/ts-mono` — the submodule pointer and dist are committed together
5. **Two merges:** the TS monorepo branch merges to its `main`; the Python branch (already containing dist) merges to its `main`

## Supporting Details

### TypeScript Monorepo Structure

#### Tooling

- **Turborepo** for build orchestration and caching
- **pnpm workspaces** for package management
- **manypkg** for monorepo configuration and dependency linting

#### Directory Structure

```
ts-monorepo/
├── apps/
│   ├── inspect/          # Frontend app for inspect_ai
│   └── scout/            # Frontend app for inspect_scout
├── packages/
│   ├── common/           # Shared non-UI utilities, types, helpers
│   └── components/       # Shared React components
├── tooling/
│   ├── eslint-config/    # Shared ESLint configuration
│   ├── prettier-config/  # Shared Prettier configuration
│   └── tsconfig/         # Shared TypeScript configurations
├── turbo.json
├── pnpm-workspace.yaml
└── package.json
```

#### Package Details

All packages use the `@tsmono` scope.

| Package | Name | Purpose |
|---------|------|---------|
| `apps/inspect` | `@tsmono/inspect-app` | `inspect_ai` frontend |
| `apps/scout` | `@tsmono/scout-app` | `inspect_scout` frontend |
| `packages/util` | `@tsmono/util` | Shared pure non-UI utilities, types, helpers |
| `packages/react` | `@tsmono/react` | Shared React components |
| `tooling/*` | `@tsmono/eslint-config`, etc. | Dev tooling configs |

#### Workspace Dependencies

Apps reference shared packages using pnpm's `workspace:*` protocol:

```json
{
  "dependencies": {
    "@tsmono/react": "workspace:*",
    "@tsmono/util": "workspace:*"
  }
}
```

This tells pnpm to resolve from the monorepo workspace rather than npm. At install time, pnpm links directly to the local package source.

#### Notes

- Apps are not published to npm; their `dist/` folders are committed to the Python repo
- The existing npm package (`@meridianlabs/inspect-scout-viewer`) for the library build is a separate concern

### Vite Output Path Detection

The Vite config automatically detects whether it's running as a submodule inside a Python repo or standalone. No environment variables or config files needed.

**How it works.** The submodule is mounted at `src/inspect_scout/_view/ts-mono/`, so from `_view/ts-mono/apps/scout/` the Python repo root is six levels up. At build time, Vite checks whether `../../../../../../pyproject.toml` exists and contains `name = "inspect_scout"`. If so, it outputs to that repo's serving path. Otherwise, it defaults to local `dist/`.

```typescript
// apps/scout/vite.config.ts

function resolveOutputDir(): string {
  const pythonRoot = resolve(__dirname, "../../../../../..");
  const pyproject = join(pythonRoot, "pyproject.toml");

  if (existsSync(pyproject)) {
    const content = readFileSync(pyproject, "utf-8");
    if (content.includes('name = "inspect_scout"')) {
      const outDir = join(pythonRoot, "src/inspect_scout/_view/dist");
      console.log(`[vite] Submodule detected — output: ${outDir}`);
      return outDir;
    }
  }

  return "dist";
}
```

The dev server (`pnpm dev`) is unaffected since it serves from memory.

### Type Generation Pipeline

Today, `openapi.json` is exported by running Python (`scripts/export_openapi_schema.py`), then `pnpm types:generate` produces `generated.ts`. After the split, the two steps live in different repos — but the cross-repo boundary is handled the same way as Vite output path detection.

**`openapi.json` stays in the Python repo.** The export script (`scripts/export_openapi_schema.py`) continues to generate it from the FastAPI app, same as today.

**`generate-types` reads from the Python repo via relative path.** Using the same pyproject.toml detection pattern as Vite, the script checks whether it's running in submodule mode. If so, it reads `openapi.json` from the Python repo. If not, it errors with a clear message — type generation is inherently a cross-repo operation and only makes sense in submodule mode.

**`generated.ts` is committed to the TS repo.** From the TS repo's perspective, `generated.ts` is checked-in source code. TS CI typechecks and tests against it without needing to regenerate. Only a frontend contributor doing story 5 (coordinated API + UI changes) regenerates it.

**CI validation.** Story 9's `generated.ts` check is performed by the `js-dist-validation` job. It regenerates types from the committed `openapi.json`, then diffs the submodule working tree. If `generated.ts` is mismatched, CI fails with a specific error message directing the contributor to regenerate types.

## Implementation and Migration

### Phase 1: Scaffold and Prove Out (iterate until confident)

Repeat this loop — testing end-to-end each time — until the monorepo structure is solid:

1. **Create the TS monorepo repo.** Scaffold with Turborepo, pnpm workspaces, shared tooling configs (`tooling/eslint-config`, `tooling/tsconfig`, etc.). Start with `apps/scout/` only.
2. **Move the scout frontend code.** Copy from `src/inspect_scout/_view/www/` into `apps/scout/`. Factor shared code into `packages/` as appropriate.
3. **Wire up the submodule.** Add submodule at `src/inspect_scout/_view/ts-mono/`. Update `pyproject.toml` artifacts path from `src/inspect_scout/_view/www/dist` to `src/inspect_scout/_view/dist`.
4. **Update Python server.** Change serving path from `www/dist` to `dist` (since `www/` no longer exists in the Python repo).

At this point, `pnpm build` in the submodule should produce a working `dist/` and `scout view` should work. Iterate on steps 1–4 until that's true.

### Phase 2: CI and Release

Once phase 1 is stable:

5. **Update CI.** Split the monolithic `build.yaml` — frontend lint/typecheck/test moves to the TS monorepo's own CI. Python-side CI validates stories 8–10: mismatched `openapi.json`, mismatched `generated.ts`, and mismatched `dist/`.
6. **NPM publishing.** Move from `src/inspect_scout/_view/www/` to the TS monorepo's own CI.

### Open Items

- [ ] Review `npm-publish.yml` in the TS monorepo — adapted from the Python repo version but needs validation (working-directory for `pnpm install` vs `npm publish`, tag-based version sync in a separate repo, `npm` environment/secrets setup on the new repo)
- [ ] Review `ci.yaml` in the TS monorepo — moved from Python repo's `build.yaml` JS jobs. Verify Playwright `--filter scout` works, confirm pnpm cache auto-detection is sufficient without explicit `cache-dependency-path`

### Phase 3: inspect_ai

7. **Add `apps/inspect/`.** Bring the `inspect_ai` frontend into the monorepo. Factor additional shared code into `packages/`.

## FAQ

**Q: I already had the repo cloned before submodules were added. What do I do?**

After pulling the commit that adds the submodule, run:

```bash
git submodule update --init
```

This registers the submodule and checks out the correct commit. You only need to do this once.

**Q: Once submodules are set up, what happens when I `git pull`?**

`git pull` updates the submodule *pointer* (which commit it should be at), but does not update the submodule's working tree. To sync the working tree after pulling:

```bash
git pull && git submodule update
```

Or configure git to do this automatically:

```bash
git config submodule.recurse true
```

**Q: How do I clone the Python repo with the submodule already initialized?**

```bash
git clone --recurse-submodules https://github.com/meridianlabs-ai/inspect_scout.git
```

**Q: How do I advance the submodule to the latest upstream commit?**

```bash
git -C src/inspect_scout/_view/ts-mono pull
```

The Python repo will now show the submodule as modified — commit the new pointer when ready.

**Q: How do I check which commit the submodule points to?**

```bash
git submodule status
```

Shows the commit SHA, the submodule path, and whether it's out of sync (prefixed with `+`).

**Q: How can I `git status` the submodule without needing to cd into it?**

Use `git -C` to run any git command against the submodule from the repo root:

```bash
git -C src/inspect_scout/_view/ts-mono status
git -C src/inspect_scout/_view/ts-mono diff
git -C src/inspect_scout/_view/ts-mono log --oneline -5
```

**Q: I prefer SSH over HTTPS for git. How do I use the submodule with SSH?**

The submodule URL in `.gitmodules` is HTTPS (works for everyone, including CI). To use SSH locally, override the URL for your clone:

```bash
git config submodule.src/inspect_scout/_view/ts-mono.url git@github.com:meridianlabs-ai/ts-mono-test.git
```

This is a local-only setting and won't affect other contributors.
