# Frontend Separation Plan: TypeScript Monorepo Migration

## Contents

1. [Problem Statement](#problem-statement)
2. [Definitions](#definitions)
3. [Requirements/User Stories](#requirementsuser-stories)
4. [Design Proposal](#design-proposal)
   - [Versioning Strategy](#versioning-strategy)
   - [React App Publishing](#react-app-publishing)
   - [React App Artifact Resolution](#react-app-artifact-resolution)
   - [Asset Fingerprinting](#asset-fingerprinting)
   - [TypeScript Monorepo Structure](#typescript-monorepo-structure)
5. [Open Topics](#open-topics)
6. [Status](#status)

## Problem Statement

Two Python packages embed React frontends: `inspect_ai` and `inspect_scout`.

Currently:

1. **TypeScript code is copied between `inspect_ai` and `inspect_scout`** - duplication, maintenance burden
2. **Built `dist/` is committed to git** - non-ideal...a bit of a smell.
3. **Code is not minified** - because `dist/` is committed, minified code would bloat history further (minified code diffs poorly).
4. **`NoCacheStaticFiles` hack** (in `inspect_scout`) disables caching to work around missing asset fingerprinting

**Goal**: Create a TypeScript monorepo with shared packages and apps for both `inspect_ai` and `inspect_scout`, while maintaining the user experience where each Python package "just works."

## Definitions

### Actors

| Actor | Description |
|-------|-------------|
| **Python package** | The `inspect-scout` or `inspect-ai` package installed via pip. Contains backend code, CLI, and serves the frontend. |
| **React app** | The React frontend application. Built output is the `dist/` folder. |
| **REST API** | The HTTP contract between Python and JS (endpoints, request/response shapes). |

### User Types

| User Type | How they install | What they expect |
|-----------|------------------|------------------|
| **End users** | `pip install inspect-scout` | Just works |
| **Main branch users** | `pip install git+https://github.com/meridianlabs-ai/inspect_scout` | Just works, zero extra steps. Want latest fixes before PyPI release. |
| **Contributors** | `git clone && pip install -e . "[dev]"` | Develop on Python, frontend, or both. May have Node.js installed. |

### Compatibility Relationships

**Python → React App**:
Python web server serves the static files of the React app from its `dist/` directory.

**React App → REST API (HTTP requests)**:
The React app makes HTTP requests to Python's REST API endpoints. The REST API is consumer-agnostic - it doesn't know or care that the React app is calling it. Compatibility is determined by whether the REST API provides the endpoints/shapes the React app expects.

**Python ↔ External persisted data**:
Python can handle backwards compatibility with old data formats.

**React App → External persisted data** (direct reads):
TBS - In some cases JS reads persisted data directly from disk. This may be just the "bundled" scenario for inspect. (Noted for future consideration, not a primary driver now.)

## Requirements/User Stories

### 1. End users install from PyPI and get a working React app

End users run `pip install inspect-scout` and get a compatible React app bundled in the wheel.

CI builds the wheel with the latest compatible React app already included. No network fetch at install time.

### 2. Main branch users install from GitHub and get a working React app

Main branch users run `pip install git+https://...` and a compatible React app is fetched during install.

A build hook runs during install, fetches the latest compatible React app from GitHub releases, and places it in `dist/`.

### 3. Contributors install editable and get a working React app

Contributors run `git clone && pip install -e . "[dev]"` and a compatible React app is fetched during install.

Same build hook as story 2. The fetched `dist/` is gitignored.

### 4. Contributor makes React-only changes (no API change required)

Contributor modifies React code without requiring any REST API changes.

- Work in the TypeScript monorepo
- Bump React app version (patch or minor)
- PR, merge, release
- Python packages automatically pick up new React releases on next install
- REST API version unchanged.

### 5. Contributor makes Python-only changes

Contributor modifies Python code (new scanner, bug fix) without changing the REST API. No React changes needed.

- Work in the Python repo as usual
- Bump Python package version
- REST API version unchanged
- No TypeScript monorepo involvement.

### 6. Contributor adds a new API endpoint and React code that uses it

Contributor adds a new endpoint (REST API minor bump) and React code that calls it. Requires coordinated changes to both repos.

1. Python Side
    - Add endpoint in Python
    - bump REST API minor version in `openapi.json`
    - bump Python package version
2. React Side
    - Add React code that uses it
    - bump `requiredApiVersion` to match
    - bump React app version
3. Release Process
    - Release Python first (new API available)
    - then React (can now use it)

### 7. Contributor makes a breaking API change

Contributor changes an existing endpoint's contract (REST API major bump). Requires coordinated release of both Python and React.

1. Make breaking change in Python, bump REST API major version, bump Python package version
2. Update React to work with new contract, bump `requiredApiVersion` to new major, bump React app version
3. Coordinate releases so users get both together

### 8. Incompatible pairings are prevented

The resolution algorithm only considers React releases whose `requiredApiVersion` is satisfied by Python's REST API version. Mismatches are rejected at install time with a clear error.

## Assumptions

- Git/editable installs require network access for the post-install hook to fetch the React app.

## Design Proposal

> The design hinges on the REST API version as the coordination point between the Python code and the React App. Because Python and React communicate solely through HTTP endpoints, the API contract determines compatibility. This allows Python and React to live in separate repositories, version independently, and release on their own schedules — the REST API version is what binds them.

### Versioning Strategy

#### REST API Version

The HTTP contract between Python and JS. Owned by the Python repo; source of truth is `API_VERSION` in `_api_v2.py` (exported to `openapi.json` → `info.version`).

| Bump | When | Examples | JS Compatibility |
|------|------|----------|------------------|
| **MAJOR** | Breaking changes | Remove endpoint, change response shape | Old dependents **break** |
| **MINOR** | Additive changes | New endpoint, new optional field | Old dependents still work |
| **PATCH** | Bug fixes | Fix incorrect response | Old dependents still works |

#### Python Package Version

Tracks Python releases: features, scanners, CLI changes. Owned by the `inspect_ai` or `inspect_scout` repo.

**This versioning approach remains unchanged.** Both packages remain pre-1.0 indefinitely, using PATCH for all regular releases.


#### React App Version

Tracks frontend releases: UI changes, new screens, bug fixes. Owned by the TypeScript monorepo.

Semver for an application (no external dependents):

| Bump | When | Examples |
|------|------|----------|
| **MAJOR** | Maintainer discretion | Major UI redesign |
| **MINOR** | New features, screens | New page, new visualization |
| **PATCH** | Bug fixes, polish | Fix rendering bug |

##### The React App's Two Attributes

The React app declares both its own version AND what REST API it requires. These live in `package.json`:

```json
{
  "name": "@meridian/scout-app",
  "version": "2.1.0",
  "requiredApiVersion": "^1.3.0"
}
```

### React App Publishing

React apps are published to **GitHub Releases** (not npm). On version tag, CI creates a release with a single asset whose filename encodes both the app version and required API version:

```
scout-app-2.1.0-api-1.3.0.tar.gz
```

Here, `2.1.0` is the app version and `1.3.0` is the minimum required API version.

### React App Artifact Resolution

Python packages resolve a compatible React app by parsing artifact filenames and selecting the latest app version whose required API version is satisfied by Python's implemented API version.

Resolution happens at wheel build time for PyPI releases, or via post-install hook for git/editable installs:

#### PyPI Wheels (End Users)

```
pip install inspect-scout
```

- **When**: CI runs the resolution algorithm before building the wheel
- **Where**: GitHub Actions
- **Result**: `dist/` is baked into the published wheel
- **User experience**: No network fetch at install time; just works

> This mirrors how `inspect_ai` downloads sandbox tools binaries from S3 at wheel build time and bundles them into the published wheel.

#### Git / Editable Installs (Contributors & Main Branch Users)

```
pip install git+https://github.com/...
pip install -e ".[dev]"
```

- **When**: Post-install hook runs during `pip install`
- **Where**: User's machine
- **Result**: `dist/` fetched on demand, gitignored
- **User experience**: Automatic; no manual steps required

#### Edge Cases

| Scenario | Behavior |
|----------|----------|
| No compatible release | Error with helpful message listing available versions |
| Network failure | Error with retry suggestion |
| `dist/` already exists | Overwrite with fetched version |
| GitHub rate limiting | Use auth token if available, else helpful error |

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

### TypeScript Monorepo Structure

#### Tooling

- **Turborepo** for build orchestration and caching
- **pnpm workspaces** for package management

#### Directory Structure

```
ts-monorepo/
├── apps/
│   ├── inspect/          # Frontend app for `inspect_ai`
│   └── scout/            # Frontend app for `inspect_scout`
├── packages/
│   └── common/           # Shared utilities, components, types
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
| `packages/common` | `@meridian/common` | Shared code (components, utils, types) |
| `tooling/*` | `@meridian/eslint-config`, etc. | Dev tooling configs |

#### Example: App `package.json`

```json
{
  "name": "@meridian/scout-app",
  "version": "2.1.0",
  "requiredApiVersion": "^1.3.0",
  "dependencies": {
    "@meridian/common": "workspace:*",
    "react": "^18.2.0"
  }
}
```

The `workspace:*` protocol tells pnpm to resolve `@meridian/common` from the monorepo workspace rather than npm. At install time, pnpm links directly to `packages/common/`.

#### Notes

- Start with a single `packages/common`; split into separate packages later if needed
- Apps are not published to npm; their `dist/` folders are published to GitHub releases
- If external consumers ever need the shared package, npm publishing can be added later

## Open Topics

- GitHub releases vs s3? If so, why didn't we do that for tool support artifacts?

### Release Process
- Who has release authority?
- How do we coordinate cross-repo releases?
- Should there be a release checklist or approval process?

### Build Hook Implementation
- How does `pip install -e .` trigger the fetch?
- Hatch build hook vs custom setup.py logic
- Error handling details

### Migration Plan
- Order of operations
- Backwards compatibility during transition
- CI/CD changes needed

### Version Pinning
- Can a Python package pin a specific React app version for reproducible builds?
