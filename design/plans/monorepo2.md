# Frontend Separation Plan v2: Commit-Pinned Artifact Distribution

## Contents

1. [Problem Statement](#problem-statement)
2. [Definitions](#definitions)
3. [Requirements](#requirements)
4. [Assumptions](#assumptions)
5. [Design Proposal](#design-proposal)
   - [Overview](#overview)
   - [Artifact Publishing](#artifact-publishing)
   - [Artifact Fetching](#artifact-fetching)
   - [Git Submodule as Coordination Point](#git-submodule-as-coordination-point)
6. [How Each Story Is Solved](#how-each-story-is-solved)
7. [Walkthrough: Coordinated Frontend + API Feature](#walkthrough-coordinated-frontend--api-feature)
8. [Supporting Details](#supporting-details)
   - [TypeScript Monorepo Structure](#typescript-monorepo-structure)
   - [Asset Fingerprinting](#asset-fingerprinting)
9. [Open Topics](#open-topics)

## Problem Statement

Two Python packages embed React frontends: `inspect_ai` and `inspect_scout`.

Currently:

1. **TypeScript code is copied between `inspect_ai` and `inspect_scout`** — duplication, maintenance burden
2. **Built `dist/` is committed to git** — bloats history, poor diffs for minified code
3. **Code is not minified** — because `dist/` is committed, minified code would bloat history further
4. **`NoCacheStaticFiles` hack** (in `inspect_scout`) disables caching to work around missing asset fingerprinting

**Goal**: Create a TypeScript monorepo with shared packages and apps for both `inspect_ai` and `inspect_scout`. Frontend build artifacts are published to S3 (keyed by commit SHA) and fetched by the Python package at build/install time. No new versioning schemes — the git commit ref is the coordination point.

## Definitions

### Key Components

| Component | Description |
|-------|-------------|
| **Python package** | `inspect-scout` or `inspect-ai`, installed via pip. Contains backend code, CLI, and serves the frontend. |
| **React app** | The React frontend application. Built output is the `dist/` folder. |
| **TS monorepo** | A separate git repository containing the TypeScript code for both apps and shared packages. |

### User Types

| User Type | Description |
|-----------|-------------|
| **PyPI user** | Consumes the published Python package from PyPI |
| **Git user** | Installs the Python package directly from a git ref |
| **Python-only contributor** | Develops Python code; does not work on frontend code |
| **Frontend contributor** | Works primarily in the TS monorepo; updates the submodule pointer in the Python repo when ready to share |
| **Python package maintainer** | Cuts releases of the Python package to PyPI |

## Requirements

| # | Title | Description |
|---|-------|-------------|
| 1 | **PyPI user** can `scout view` after installing from PyPI | `pip install inspect-scout` provides a working frontend. No extra steps, no network fetch at install time. |
| 2 | **Git user** can `scout view` after installing a git ref | `pip install git+https://...[@ref]` provides a working frontend. No extra steps beyond having network access. |
| 3 | **Python-only contributor** can `scout view` after `pip install -e`'ing | `git clone && pip install -e ".[dev]"` provides a working frontend automatically. Python-only changes require no frontend awareness. |
| 4 | **Frontend contributor** can test WIP via Python server | A frontend contributor can serve their in-progress frontend through the Python server locally, verifying it works end-to-end before publishing. |
| 5 | **Frontend contributor** can prepare WIP branch for others to test | A frontend contributor can make their in-progress frontend available so that others can test it before the changes are merged to `main`. |
| 6 | **Git user** can test a prepared WIP branch | A git user can install a Python branch and get the matching in-progress frontend automatically, without needing Node.js or the TS monorepo. |
| 7 | **Frontend contributor** can make completed changes available on Python `main` | Iterates locally across many commits. Publishing is a manual decision, deferred until ready to share, equivalent to today's "build and commit dist/." Must happen after committing so there's a commit SHA to key on. |
| 8 | **Python package maintainer** can publish a release that includes the correct frontend | When a maintainer cuts a release, the resulting wheel includes the correct frontend build. No manual steps beyond the normal release process. |

## Assumptions

- Only the frontend contributor requires Node.js. All other user types must work without Node.js installed.
- Git/editable installs require network access for the build hook to fetch the frontend artifact from S3.
- The S3 bucket is publicly readable (or uses a well-known auth mechanism).
- The TS monorepo CI or the developer's publish script is responsible for building and uploading artifacts. Python never builds TypeScript.

## Design Proposal

### Overview

The TypeScript code for both `inspect_ai` and `inspect_scout` frontends lives in a **separate git repository** (the TS monorepo), managed with **pnpm workspaces** and **Turborepo**. Shared code (components, utilities, types) is factored into workspace packages consumed by both apps.

The Python repo includes the TS monorepo as a **git submodule** at `frontend/`. The submodule pointer — a commit SHA tracked by git itself — is the single coordination point between the Python package and its frontend. No semver, no compatibility ranges — the pointer says "I need this exact build."

When a frontend contributor is ready to share their work, they **build and publish** the app's `dist/` as a `.tar.gz` to **S3**, keyed by the TS monorepo commit SHA (e.g., `s3://app-dist/scout-app/{sha}.tar.gz`). The decision to publish is deliberate — equivalent to today's decision to "build and commit `dist/`." A script handles the actual build, tar, and upload.

Non-frontend users never need Node.js. A **build hook** in the Python package reads the submodule pointer SHA, fetches the matching artifact from S3, and extracts it to `frontend/apps/scout/dist/`. For PyPI wheels, CI does this at build time so the wheel ships with `dist/` included. The Python server always serves from the same path — `frontend/apps/scout/dist/` — regardless of how the files got there.

### Artifact Publishing

Frontend artifacts are published to a publicly readable S3 bucket (`app-dist`) in the Meridian AWS account.

#### S3 Structure

```
s3://app-dist/
├── scout-app/
│   ├── {commit-sha-1}.tar.gz
│   ├── {commit-sha-2}.tar.gz
│   └── ...
└── inspect-app/
    ├── {commit-sha-1}.tar.gz
    ├── {commit-sha-2}.tar.gz
    └── ...
```

Each artifact carries S3 object metadata for auditability:

| Metadata key | Value | Example |
|-------------|-------|---------|
| `branch` | Source branch at publish time | `main`, `feat/new-chart` |
| `publisher` | Git username of the publisher | `jdoe` |

#### Publish Script

The TS monorepo provides a script (e.g., `pnpm publish:scout`) that:

1. Reads the current HEAD commit SHA (the script must run after committing — uncommitted changes have no SHA to key on)
2. Runs `pnpm build` for the target app
3. Tars the `dist/` directory
4. Triggers a GitHub Action (or similar) that uploads to `s3://app-dist/{app-name}/{commit-sha}.tar.gz`

The developer does not upload directly to S3. The upload is handled by CI (e.g., a GitHub Actions workflow) that has the necessary credentials. The local script's role is to build, tar, and initiate the upload — not to hold S3 write credentials.

**Publishing is deferred until sharing.** A frontend developer can make many local commits without publishing. They only run the publish script when they're ready for someone else to consume the build — e.g., before updating the submodule pointer for a tester, or before merging to main. This mirrors today's workflow where a developer can iterate locally and only commits `dist/` when they're ready to share.

#### When Artifacts Are Published

| Scenario | Who publishes | Trigger |
|----------|---------------|---------|
| Frontend-only updates | Frontend contributor | Manual script run when ready to share |
| Coordinated frontend + API changes | Frontend contributor | Manual script run when ready for testing |
| TS monorepo CI (optional) | CI | Could auto-publish on merge to main |

### Artifact Fetching

When a user runs `pip install` (any variant), the frontend assets need to end up at `frontend/apps/scout/dist/`. This section describes how that happens.

#### How pip Triggers the Fetch

Even for commands like `pip install -e .`, pip internally builds a wheel before installing it. This project uses **Hatch** as its build backend, and Hatch supports **custom build hooks** — a Python file (`hatch_build.py`) at the project root that runs automatically during every wheel build. The fetch logic lives in this hook.

The hook:

1. Reads the submodule pointer SHA via `git ls-tree HEAD frontend`
2. Constructs the S3 URL: `https://app-dist.s3.amazonaws.com/{app-name}/{sha}.tar.gz`
3. Downloads and extracts to `frontend/apps/scout/dist/`
4. For non-editable builds, uses `build_data["force_include"]` to ensure `dist/` is included in the wheel

#### When Fetching Happens

| Install method | What happens | Target path |
|----------------|-------------|-------------|
| `pip install inspect-scout` (PyPI) | Nothing — `dist/` was baked into the wheel by CI | `frontend/apps/scout/dist/` |
| `pip install git+https://...` | pip clones the repo, builds a wheel; the hook fetches from S3 during the build | `frontend/apps/scout/dist/` |
| `pip install -e ".[dev]"` | pip builds an editable wheel; the hook fetches from S3 during the build | `frontend/apps/scout/dist/` |
| `python -m build` / `hatch build` (CI) | The hook fetches from S3 during the wheel build | `frontend/apps/scout/dist/` baked into wheel |

#### Serving Path

The Python server always serves from `frontend/apps/scout/dist/`. This path is the same regardless of install method — the only difference is how the files got there (hook fetch, local `pnpm build`, or baked into the wheel by CI).

#### Dependencies

The hook uses only Python stdlib (`urllib.request`, `tarfile`, `subprocess`) — no extra build dependencies needed beyond what's already in `build-system.requires`.

#### Error Handling

| Scenario | Behavior |
|----------|----------|
| Artifact not found in S3 | Error: "Frontend build for commit {sha} not found. Has it been published?" |
| Network failure | Error with retry suggestion |
| `dist/` already exists (editable) | Overwrite with fetched version |

### Git Submodule as Coordination Point

The Python repo declares the TS monorepo as a git submodule at `frontend/`:

```
inspect_scout/
├── .gitmodules          # declares frontend/ → https://github.com/.../ts-monorepo
├── frontend/            # submodule pointer (not checked out unless initialized)
├── src/
└── pyproject.toml
```

Most users never initialize the submodule. Git still records the pointer as a SHA in the tree, and the build hook reads it via `git ls-tree HEAD frontend` — no checkout required.

Only frontend contributors initialize the submodule (via `git submodule init && git submodule update`) to get a working copy of the TS monorepo for local development.

#### Submodule State

- On `main`, the submodule pointer always points to a published artifact
- On feature branches, may point to a branch commit artifact for testing
- Updated by the frontend contributor when they're ready to share a new build

## How Each Story Is Solved

**Story 1 (PyPI user):** The wheel published to PyPI already contains `dist/`. Nothing special happens at install time.

**Story 2 (Git user):** A build hook runs during `pip install`, reads the submodule pointer SHA, downloads the matching artifact from S3, and extracts it to `frontend/apps/scout/dist/` — the same location `pnpm build` would produce.

**Story 3 (Python-only contributor):** Same build hook as story 2. The submodule pointer stays the same across Python-only changes.

**Story 4 (Frontend contributor tests WIP locally):** The frontend contributor initializes the submodule (`git submodule init && git submodule update`) and runs `pnpm build` inside it. The output lands at `frontend/apps/scout/dist/` — the same path the build hook and `pnpm build` both target. No symlinks needed. They run `scout view` to verify end-to-end.

**Story 5 (Frontend contributor prepares WIP for others):** The frontend contributor commits in the TS monorepo, runs the publish script to upload the artifact to S3, then updates the submodule pointer on a Python branch and commits.

**Story 6 (Git user tests prepared WIP):** The git user installs the Python branch (`pip install git+https://...@feature-branch`). The build hook reads the submodule pointer SHA, fetches the matching artifact from S3, and extracts it to `frontend/apps/scout/dist/`. No Node.js or TS monorepo needed.

**Story 7 (Frontend contributor publishes):** The TS monorepo provides a publish script that builds `dist/`, tars it, and uploads to S3 keyed by the current HEAD commit SHA. The contributor then updates the submodule pointer in the Python repo and commits.

**Story 8 (Python release):** CI reads the submodule pointer SHA, fetches the matching tarball from S3, and bakes `dist/` into the wheel at `frontend/apps/scout/dist/`. The wheel is published to PyPI. No manual steps beyond the normal release process.

## Walkthrough: Coordinated Frontend + API Feature

This traces the full lifecycle of a feature that requires both a new Python API endpoint and React code that uses it — from development through testing, merge, and release.

### 1. Developer sets up the Python repo

```bash
git clone https://github.com/.../inspect_scout
cd inspect_scout
pip install -e ".[dev]"
```

The build hook runs during `pip install -e`, fetches the current `main` frontend artifact from S3, and places it at `frontend/apps/scout/dist/`. The developer now has a working baseline.

### 2. Developer builds the Python side

Create a feature branch and add the new endpoint:

```bash
git checkout -b feat/chart-export
# ... add new endpoint, write tests ...
scout view  # verify existing frontend still works against the new code
git push -u origin feat/chart-export
```

### 3. Developer sets up the TS monorepo

The developer initializes the submodule to get a working copy of the frontend code:

```bash
git submodule init && git submodule update
cd frontend
pnpm install
```

### 4. Developer builds the frontend side

In the TS monorepo (`frontend/`), on a feature branch:

```bash
git checkout -b feat/chart-export
# ... add React code that calls the new endpoint ...
pnpm dev  # dev server with hot reload, proxied to the local Python server
# iterate across multiple commits — no publishing yet
```

### 5. Developer tests end-to-end locally

Build the frontend and verify it works through the Python server:

```bash
cd frontend
pnpm build  # produces frontend/apps/scout/dist/
cd ..
scout view  # Python server serves the locally built frontend
```

The developer verifies the new feature works end-to-end. They can repeat steps 4–5 as many times as needed.

### 6. Developer makes the branch available to a tester

When the developer is ready for someone else to test, they publish the frontend artifact:

In the TS monorepo (`frontend/`):

```bash
git push origin feat/chart-export
pnpm publish:scout  # builds dist/, tars it, triggers CI upload to s3://app-dist/scout-app/{sha}.tar.gz
```

Back in the Python repo, update the submodule pointer to the published commit:

```bash
cd frontend && git checkout {sha} && cd ..
git add frontend
git commit -m "Update frontend to feat/chart-export"
git push
```

### 7. Tester consumes the branch

The tester does not need Node.js, the TS monorepo, or any frontend tooling. They run:

```bash
pip install git+https://github.com/.../inspect_scout@feat/chart-export
scout view
```

pip clones the Python branch, builds a wheel, and the build hook reads the submodule pointer SHA, fetches the matching artifact from S3, and extracts it to `frontend/apps/scout/dist/`. The tester gets the complete feature.

### 8. Developer merges to main

After testing and review:

- Merge the TS monorepo branch to `main` (the published artifact is already in S3, keyed by the commit SHA — merging doesn't change the SHA)
- If the TS merge changed the SHA (e.g., squash merge), re-publish from the new SHA and update the submodule pointer in the Python repo
- Merge the Python branch to `main`

Anyone installing from `main` now gets the new feature automatically via the build hook.

### 9. Maintainer publishes to PyPI

When the maintainer is ready to cut a release:

```bash
python -m build  # or CI pipeline
# The build hook fetches the artifact from S3 and bakes dist/ into the wheel
# Publish the wheel to PyPI
```

End users run `pip install inspect-scout` and get the new feature with no extra steps.

## Supporting Details

### TypeScript Monorepo Structure

#### Tooling

- **Turborepo** for build orchestration and caching
- **pnpm workspaces** for package management

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

All packages use the `@meridian/` scope.

| Package | Name | Purpose |
|---------|------|---------|
| `apps/inspect` | `@meridian/inspect-app` | `inspect_ai` frontend |
| `apps/scout` | `@meridian/scout-app` | `inspect_scout` frontend |
| `packages/common` | `@meridian/common` | Shared non-UI utilities, types, helpers |
| `packages/components` | `@meridian/components` | Shared React components |
| `tooling/*` | `@meridian/eslint-config`, etc. | Dev tooling configs |

#### Workspace Dependencies

Apps reference shared packages using pnpm's `workspace:*` protocol:

```json
{
  "dependencies": {
    "@meridian/common": "workspace:*",
    "@meridian/components": "workspace:*"
  }
}
```

This tells pnpm to resolve from the monorepo workspace rather than npm. At install time, pnpm links directly to the local package source.

#### Notes

- `common` holds non-UI code (types, utilities, helpers); `components` holds shared React components
- Apps are not published to npm; their `dist/` folders go to S3
- The existing npm package (`@meridianlabs/inspect-scout-viewer`) for the library build is a separate concern

### Asset Fingerprinting

#### The Problem

Current Vite config produces non-hashed filenames:

```javascript
// vite.config.ts
output: {
  entryFileNames: `assets/index.js`,      // No hash
  chunkFileNames: `assets/[name].js`,     // No hash
  assetFileNames: `assets/[name].[ext]`,  // No hash
}
```

Result: Browsers cache `index.js`, serve stale versions after upgrades.

#### Current Workaround

[server.py](../../src/inspect_scout/_view/server.py) has `NoCacheStaticFiles` that disables caching for all JS files.

#### Proposed Solution

Add content hashes to Vite output:

```javascript
output: {
  entryFileNames: `assets/[name]-[hash].js`,
  chunkFileNames: `assets/[name]-[hash].js`,
  assetFileNames: `assets/[name]-[hash].[ext]`,
}
```

Then remove `NoCacheStaticFiles` and use standard `StaticFiles`.

#### Why This Works

- Each build produces unique filenames based on content
- `index.html` references the hashed filenames
- Browsers cache forever (files are immutable)
- New deployments = new URLs = no stale cache

## Open Topics

### Artifact Upload Security
- The S3 bucket must be writable by authorized publishers but not by the public. Anyone with write access can push an artifact that all users will consume.
- Options: CI-only uploads (only merged commits get published via GitHub Actions with OIDC), a signing/gating service, scoped IAM credentials for trusted contributors, etc.
- What's the threat model? Compromised contributor credentials? Malicious PRs that trigger CI publish?

### Migration Plan
- Order of operations for moving TS code to the new monorepo
- Transition period where both old (committed dist/) and new (S3 fetch) coexist
- CI/CD changes needed

### Artifact Immutability
- Can a commit SHA's artifact be overwritten? (Simpler but less safe)
- Or strictly immutable? (Safer but requires new commits for fixes)

### Stale Submodule Pointer Detection
- A frontend contributor could publish a new artifact to S3 but forget to update the submodule pointer in the Python repo. The Python package would continue to serve the old frontend.
- Using a git submodule makes this harder to forget than a manual `pyproject.toml` edit — `git status` and `git diff` show submodule state changes. But the risk isn't eliminated entirely.
- CI could check that the submodule pointer matches a published artifact in S3.

### Offline/Cached Fallback for Editable Installs
- If a Python-only contributor already has a working `dist/` and re-runs `pip install -e .` (e.g., after a rebase or environment rebuild), must they have network access?
- Could the build hook skip the fetch if the correct `dist/` is already present?
