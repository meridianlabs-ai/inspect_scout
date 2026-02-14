# Frontend Separation Plan v2: Commit-Pinned Artifact Distribution

## Contents

1. [Problem Statement](#problem-statement)
2. [Definitions](#definitions)
3. [Requirements](#requirements)
4. [Design Proposal](#design-proposal)
   - [Git Submodule as Coordination Point](#git-submodule-as-coordination-point)
   - [Artifact Publishing](#artifact-publishing)
   - [Artifact Resolution](#artifact-resolution)
   - [Asset Fingerprinting](#asset-fingerprinting)
   - [TypeScript Monorepo Structure](#typescript-monorepo-structure)
5. [Open Topics](#open-topics)

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
| 3 | **Python-only contributor** can `scout view` after `pip instal -e`'ing | `git clone && pip install -e ".[dev]"` provides a working frontend automatically. Python-only changes require no frontend awareness. |
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

> The design hinges on the **git commit SHA** as the coordination point between Python and the React app. The Python repo includes the TS monorepo as a **git submodule** — git itself tracks the pinned commit. Artifacts are stored in S3 keyed by `{app-name}/{commit-sha}`. No semver, no compatibility ranges — the submodule pointer is an explicit "I need this exact build."

### How Each Story Is Solved

**Story 1 (PyPI user):** CI reads the submodule pointer SHA, fetches the matching artifact from S3, and bakes `dist/` into the wheel. No network fetch at install time.

**Story 2 (Git user):** A build hook runs during `pip install`, reads the submodule pointer SHA, downloads the matching artifact from S3, and extracts it to `dist/`.

**Story 3 (Python-only contributor):** Same build hook as story 2. The fetched `dist/` is gitignored. The submodule pointer stays the same across Python-only changes.

**Story 4 (Frontend contributor tests WIP locally):** The frontend contributor can work inside the submodule directory (`frontend/`) or in a separate clone of the TS monorepo. Either way, they build `dist/` locally and symlink it into the Python package's expected location. They run `scout view` to verify their changes end-to-end before publishing.

**Story 5 (Frontend contributor prepares WIP for others):** The frontend contributor commits in the TS monorepo, runs the publish script to upload the artifact to S3, then updates the submodule pointer on a Python branch and commits.

**Story 6 (Git user tests prepared WIP):** The git user installs the Python branch (`pip install git+https://...@feature-branch`). The build hook reads the submodule pointer SHA, fetches the matching artifact from S3, and extracts it to `dist/`. No Node.js or TS monorepo needed.

**Story 7 (Frontend contributor publishes):** The TS monorepo provides a publish script that builds `dist/`, tars it, and uploads to S3 keyed by the current HEAD commit SHA. The contributor then updates the submodule pointer in the Python repo and commits.

**Story 8 (Python release):** CI reads the submodule pointer SHA, fetches the matching tarball from S3, bakes `dist/` into the wheel, and publishes to PyPI. No manual steps beyond the normal release process.

### Artifact Publishing

Frontend artifacts are published to S3 via a script in the TS monorepo.

#### S3 Structure

```
s3://bucket-name/
├── scout-app/
│   ├── {commit-sha-1}.tar.gz
│   ├── {commit-sha-2}.tar.gz
│   └── ...
└── inspect-app/
    ├── {commit-sha-1}.tar.gz
    ├── {commit-sha-2}.tar.gz
    └── ...
```

#### Publish Script

The TS monorepo provides a script (e.g., `pnpm publish:scout`) that:

1. Reads the current HEAD commit SHA (the script must run after committing — uncommitted changes have no SHA to key on)
2. Runs `pnpm build` for the target app
3. Tars the `dist/` directory
4. Uploads to `s3://{bucket}/{app-name}/{commit-sha}.tar.gz`

**Publishing is deferred until sharing.** A frontend developer can make many local commits without publishing. They only run the publish script when they're ready for someone else to consume the build — e.g., before updating the submodule pointer for a tester, or before merging to main. This mirrors today's workflow where a developer can iterate locally and only commits `dist/` when they're ready to share.

#### When Artifacts Are Published

| Scenario | Who publishes | Trigger |
|----------|---------------|---------|
| Frontend-only updates | Frontend contributor | Manual script run when ready to share |
| Coordinated frontend + API changes | Frontend contributor | Manual script run when ready for testing |
| TS monorepo CI (optional) | CI | Could auto-publish on merge to main |

### Artifact Resolution

Python packages resolve their frontend by reading the submodule pointer SHA and fetching the matching artifact from S3.

#### Resolution Algorithm

```
1. Read commit SHA from submodule pointer (git ls-tree HEAD frontend)
2. Construct S3 URL: s3://{bucket}/{app-name}/{sha}.tar.gz
3. Download and extract to dist/
```

#### When Resolution Happens

| Install method | When | Where | Result |
|----------------|------|-------|--------|
| `pip install inspect-scout` (PyPI) | CI wheel build | GitHub Actions | `dist/` baked into wheel |
| `pip install git+https://...` | Build hook during install | User's machine | `dist/` fetched on demand |
| `pip install -e ".[dev]"` | Build hook during install | User's machine | `dist/` fetched on demand, gitignored |

#### Error Handling

| Scenario | Behavior |
|----------|----------|
| Artifact not found in S3 | Error: "Frontend build for commit {sha} not found. Has it been published?" |
| Network failure | Error with retry suggestion |
| `dist/` already exists (editable) | Overwrite with fetched version |
| S3 auth failure | Error with credential guidance |

### Git Submodule as Coordination Point

The Python repo includes the TS monorepo as a git submodule. The submodule pointer is the single source of truth for which frontend commit the Python package needs.

#### Repository Structure

```
inspect_scout/
├── .gitmodules          # declares frontend/ → https://github.com/.../ts-monorepo
├── frontend/            # submodule pointer (not checked out unless initialized)
├── src/
└── pyproject.toml
```

The submodule is **not initialized** for most users. It's just a SHA pointer in the git tree. The build hook reads the SHA via `git ls-tree HEAD frontend` — this works without initializing the submodule.

#### How the Build Hook Reads the SHA

The build hook needs the submodule pointer SHA to construct the S3 URL. It does **not** need the submodule contents.

| Install method | `.git` available? | How to read SHA |
|----------------|-------------------|-----------------|
| `pip install -e .` (editable) | Yes — user's clone | `git ls-tree HEAD frontend` |
| `pip install git+https://...` | Yes — pip clones the repo with `.git` | `git ls-tree HEAD frontend` |
| CI wheel build | Yes — CI checks out the repo | `git ls-tree HEAD frontend` |
| sdist | No — `.git` is stripped | Fallback: bake SHA into a generated file during sdist creation |

pip initializes submodules automatically during `git+https://` installs ([pypa/pip#289](https://github.com/pypa/pip/issues/289)), but the build hook doesn't even need that — it only reads the pointer from the parent repo's tree.

#### Submodule State

- On `main`, the submodule pointer always points to a published artifact
- On feature branches, may point to a branch commit artifact for testing
- Updated by the frontend contributor when they're ready to share a new build

### Asset Fingerprinting

#### The Problem

Current Vite config produces non-hashed filenames:

```javascript
output: {
  entryFileNames: `assets/index.js`,
  chunkFileNames: `assets/[name].js`,
  assetFileNames: `assets/[name].[ext]`,
}
```

Browsers cache `index.js` and serve stale versions after upgrades.

#### Current Workaround

`NoCacheStaticFiles` in `server.py` disables caching for all JS files.

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

#### Notes

- `common` holds non-UI code (types, utilities, helpers); `components` holds shared React components
- Apps are not published to npm; their `dist/` folders go to S3
- The existing npm package (`@meridianlabs/inspect-scout-viewer`) for the library build is a separate concern

## Open Topics

### S3 Bucket
- Which AWS account/bucket?
- Public read access or authenticated?
- Lifecycle policies for old artifacts?

### Build Hook Implementation
- Hatch build hook vs custom mechanism for fetching from S3 during `pip install -e .`
- How to handle the hook for `pip install git+https://...` (same hook, different trigger?)

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
