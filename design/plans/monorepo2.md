# Frontend Separation Plan v2: Commit-Pinned Artifact Distribution

## Contents

1. [Problem Statement](#problem-statement)
2. [Definitions](#definitions)
3. [Requirements](#requirements)
4. [Design Proposal](#design-proposal)
   - [Artifact Publishing](#artifact-publishing)
   - [Artifact Resolution](#artifact-resolution)
   - [Frontend Commit Ref in Python](#frontend-commit-ref-in-python)
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

### Actors

| Actor | Description |
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
| **Frontend contributor** | Works primarily in the TS monorepo; touches the Python repo to update the frontend commit ref |
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

> The design hinges on the **git commit SHA** as the coordination point between Python and the React app. The Python repo pins the exact TS monorepo commit it needs in `pyproject.toml`. Artifacts are stored in S3 keyed by `{app-name}/{commit-sha}`. No semver, no compatibility ranges — the pin is an explicit "I need this exact build."

### How Each Story Is Solved

**Story 1 (PyPI user):** CI reads the pinned commit ref from `pyproject.toml`, fetches the matching artifact from S3, and bakes `dist/` into the wheel. No network fetch at install time.

**Story 2 (Git user):** A build hook runs during `pip install`, reads the commit ref from `pyproject.toml`, downloads the matching artifact from S3, and extracts it to `dist/`.

**Story 3 (Python-only contributor):** Same build hook as story 2. The fetched `dist/` is gitignored. The pinned commit ref stays the same across Python-only changes.

**Story 4 (Frontend contributor tests WIP locally):** The frontend contributor builds `dist/` locally in the TS monorepo, then copies or symlinks it into the Python package's expected location. They run `scout view` to verify their changes end-to-end before publishing.

**Story 5 (Frontend contributor prepares WIP for others):** The frontend contributor runs the publish script from their TS monorepo branch, uploading the artifact to S3 keyed by commit SHA. They then update `pyproject.toml` on a Python branch to point to that commit SHA.

**Story 6 (Git user tests prepared WIP):** The git user installs the Python branch (`pip install git+https://...@feature-branch`). The build hook reads the commit ref from `pyproject.toml`, fetches the matching artifact from S3, and extracts it to `dist/`. No Node.js or TS monorepo needed.

**Story 7 (Frontend contributor publishes):** The TS monorepo provides a publish script that builds `dist/`, tars it, and uploads to S3 keyed by the current HEAD commit SHA. The contributor then updates the commit ref in the Python repo's `pyproject.toml`.

**Story 8 (Clean merge):** Merge the TS monorepo branch to main first, (optionally) republish from main, update the Python branch's `pyproject.toml` to point to the final TS main commit SHA, then merge the Python branch to main.

**Story 9 (Python release):** CI reads the commit ref from `pyproject.toml`, fetches the matching tarball from S3, bakes `dist/` into the wheel, and publishes to PyPI. No manual steps beyond the normal release process.

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

**Publishing is deferred until sharing.** A frontend developer can make many local commits without publishing. They only run the publish script when they're ready for someone else to consume the build — e.g., before asking a tester to try a Python branch that pins that commit, or before merging to main. This mirrors today's workflow where a developer can iterate locally and only commits `dist/` when they're ready to share.

#### When Artifacts Are Published

| Scenario | Who publishes | Trigger |
|----------|---------------|---------|
| Frontend-only updates | Frontend contributor | Manual script run when ready to share |
| Coordinated frontend + API changes | Frontend contributor | Manual script run when ready for testing |
| TS monorepo CI (optional) | CI | Could auto-publish on merge to main |

### Artifact Resolution

Python packages resolve their frontend by reading the commit ref from `pyproject.toml` and fetching the matching artifact from S3.

#### Resolution Algorithm

```
1. Read commit SHA from pyproject.toml
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

### Frontend Commit Ref in Python

The Python repo stores the TS monorepo commit ref in `pyproject.toml` under a custom metadata field:

```toml
[tool.inspect-scout]
frontend-commit = "a1b2c3d4e5f6..."
```

- Updated manually by the developer when they want a new frontend build
- On main, always points to a published artifact
- On feature branches, may point to a branch commit artifact for testing

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

### Stale Commit Ref Detection
- A frontend contributor could publish a new artifact to S3 but forget to update the commit SHA in the Python repo's `pyproject.toml`. The Python package would continue to serve the old frontend.
- This is analogous to today's risk of updating JS source but forgetting to rebuild and commit `dist/`. Today, CI warns if JS source has changed without a corresponding `dist/` update.
- What's the equivalent safety net in v2? CI check that the pinned SHA is reachable from TS monorepo main? A check that the SHA was published recently? Or is code review sufficient?

### Offline/Cached Fallback for Editable Installs
- If a Python-only contributor already has a working `dist/` and re-runs `pip install -e .` (e.g., after a rebase or environment rebuild), must they have network access?
- Could the build hook skip the fetch if the correct `dist/` is already present?

## Appendix: Changes from v1

| Aspect | v1 | v2 |
|--------|----|----|
| **Coordination point** | REST API semver | Git commit SHA |
| **Versioning** | Semver for REST API, React app, and compatibility ranges | No new versioning; existing Python package versioning unchanged |
| **Artifact storage** | GitHub Releases | S3 |
| **Artifact naming** | `{app}-{app-version}-api-{api-version}.tar.gz` | `{app-name}/{commit-sha}.tar.gz` |
| **Compatibility check** | Semver range matching (`requiredApiVersion: ^1.3.0`) | Implicit — the Python repo pins the exact commit it needs |
