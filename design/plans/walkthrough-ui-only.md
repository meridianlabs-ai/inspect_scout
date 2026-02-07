# Walkthrough: UI-Only Change (Story 4)

> A frontend contributor makes a UI change that doesn't require any Python API modifications.

## Prerequisites

- Python repo cloned with submodule initialized and `pnpm install` done (one-time setup):
  ```bash
  git submodule update --init
  cd src/inspect_scout/_view/ts-mono && pnpm install
  ```

## Steps

### 1. Branch

Create a feature branch in both repos. The TS monorepo branch is where you develop; the Python repo branch is where you publish.

```bash
# Python repo
git checkout -b feature/my-ui-change

# TS monorepo
cd src/inspect_scout/_view/ts-mono
git checkout -b feature/my-ui-change
```

### 2. Develop and test

Start the Python backend and your preferred frontend dev workflow, then iterate on your changes.

```bash
# Terminal 1 — Python backend
scout view

# Terminal 2 — pick one:
pnpm dev     # Vite dev server with HMR (separate port, proxies API requests)
pnpm watch   # Rebuilds dist/ on change (uses the Python server directly)
```

Edit files under `apps/scout/` (or `packages/` for shared code).

### 3. Build

Build the production bundle. Vite detects the submodule and outputs directly to the Python repo's serving path.

```bash
pnpm build
# Output: src/inspect_scout/_view/dist/
```

### 5. Verify

Run `scout view` against the production build to confirm it works end-to-end.

### 6. Commit to the TS monorepo

```bash
cd src/inspect_scout/_view/ts-mono
git add .
git commit -m "feat: description of the UI change"
git push origin feature/my-ui-change
```

Merge the TS monorepo PR through its normal review process.

### 7. Commit to the Python repo

Back in the Python repo root, commit the updated `dist/` and the submodule pointer (which now points to your merged TS commit).

```bash
# Update submodule pointer to the merged commit
cd src/inspect_scout/_view/ts-mono && git checkout main && git pull && cd ../../../..

git add src/inspect_scout/_view/dist/ src/inspect_scout/_view/ts-mono
git commit -m "feat: description of the UI change"
git push origin feature/my-ui-change
```

Merge the Python repo PR. CI (story 8) validates that `dist/` matches the submodule pointer.

## What others see

- **Python-only contributors** and **git users** get the updated frontend automatically on their next `git pull` — no Node.js needed.
- **PyPI users** get it in the next release.
