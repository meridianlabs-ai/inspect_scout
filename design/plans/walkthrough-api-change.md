# Walkthrough: Coordinated API + UI Change (Story 5)

> A frontend contributor adds or modifies a Python API endpoint and builds frontend features against it.

## Prerequisites

- Python repo cloned with submodule initialized and `pnpm install` done (one-time setup):
  ```bash
  git submodule update --init
  cd src/inspect_scout/_view/ts-mono && pnpm install
  ```

## Steps

### 1. Branch

Create a feature branch in both repos.

```bash
# Python repo
git checkout -b feature/my-api-change

# TS monorepo
cd src/inspect_scout/_view/ts-mono
git checkout -b feature/my-api-change
```

### 2. Update the Python API

Make your changes to the Python API models and endpoints.

### 3. Regenerate TypeScript types

```bash
# From the Python repo root
.venv/bin/python scripts/export_openapi_schema.py

# From src/inspect_scout/_view/ts-mono/
pnpm types:generate
```

This reads the updated `openapi.json` from the Python repo (via the submodule's relative path) and writes `generated.ts` in the TS monorepo.

### 4. Develop and test

Start the Python backend and your preferred frontend dev workflow, then iterate on your changes.

```bash
# Terminal 1 — Python backend
scout view

# Terminal 2 — pick one:
pnpm dev     # Vite dev server with HMR (separate port, proxies API requests)
pnpm watch   # Rebuilds dist/ on change (uses the Python server directly)
```

Edit files under `apps/scout/` (or `packages/` for shared code). If you change the API again during development, repeat step 3.

### 5. Build

Build the production bundle. Vite detects the submodule and outputs directly to the Python repo's serving path.

```bash
pnpm build
# Output: src/inspect_scout/_view/dist/
```

### 6. Verify

Run `scout view` against the production build to confirm it works end-to-end.

### 7. Commit to the TS monorepo

```bash
cd src/inspect_scout/_view/ts-mono
git add .
git commit -m "feat: description of the change"
git push origin feature/my-api-change
```

Merge the TS monorepo PR through its normal review process.

### 8. Commit to the Python repo

Back in the Python repo root, commit everything together: API changes, updated `openapi.json`, `dist/`, and the submodule pointer.

```bash
# Update submodule pointer to the merged commit
cd src/inspect_scout/_view/ts-mono && git checkout main && git pull && cd ../../../..

git add src/
git commit -m "feat: description of the change"
git push origin feature/my-api-change
```

Merge the Python repo PR. CI (story 8) validates that `dist/` matches the submodule pointer — this implicitly catches stale `generated.ts` as well.

## What others see

- **Python-only contributors** and **git users** get the updated API and frontend automatically on their next `git pull` — no Node.js needed.
- **PyPI users** get it in the next release.
