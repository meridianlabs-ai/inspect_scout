# Frontend Submodule Guide

## What Changed

The frontend TypeScript code has moved from an in-repo directory to a **separate git repository** (a pnpm/Turborepo monorepo), linked back here via a **git submodule** at:

```
src/inspect_scout/_view/frontend/
```

The built `dist/` is still committed to this repo, so **Python-only contributors and end users are unaffected** — `git clone && pip install -e ".[dev]"` and `pip install inspect-scout` work exactly as before, with no Node.js required.

**Only frontend contributors** need to be aware of the changes described below.

## One-Time Setup

### Existing clone (you already have the repo)

After pulling the commit that adds the submodule:

```bash
git submodule update --init
cd src/inspect_scout/_view/frontend
pnpm install
```

### Fresh clone

```bash
git clone --recurse-submodules https://github.com/meridianlabs-ai/inspect_scout.git
cd inspect_scout/src/inspect_scout/_view/frontend
pnpm install
```

### Prefer SSH?

The submodule URL in `.gitmodules` is HTTPS (works for everyone, including CI). To use SSH locally:

```bash
git config submodule.src/inspect_scout/_view/frontend.url git@github.com:meridianlabs-ai/ts-mono-test.git
```

This is local-only and won't affect other contributors.

## Keeping in Sync

`git pull` updates the submodule **pointer** (which commit it should be at) but does **not** update the submodule's working tree. After pulling:

```bash
git submodule update
```

Or configure git to do this automatically:

```bash
git config submodule.recurse true
```

With this setting, `git pull` will also update the submodule working tree.

## Development Workflows

### UI-only changes

Changes that don't touch the Python API.

1. Work in the submodule on a feature branch:
   ```bash
   cd src/inspect_scout/_view/frontend
   git checkout -b my-feature
   pnpm dev    # hot reload dev server
   # or: pnpm watch
   ```
2. Build into the Python repo:
   ```bash
   pnpm build  # outputs to src/inspect_scout/_view/dist/
   ```
3. Commit both the dist and the submodule pointer from the Python repo root:
   ```bash
   cd ../../../..  # back to Python repo root
   git add src/inspect_scout/_view/dist/ src/inspect_scout/_view/frontend
   git commit -m "Update frontend"
   ```
4. Merge both repos: the TS monorepo branch merges to its `main`; the Python branch merges to its `main`.

### Coordinated API + UI changes

Changes that require new or modified Python API endpoints.

1. Update the Python API models
2. Re-export the OpenAPI schema:
   ```bash
   .venv/bin/python scripts/export_openapi_schema.py
   ```
3. Regenerate TypeScript types (from inside the submodule):
   ```bash
   cd src/inspect_scout/_view/frontend
   pnpm types:generate
   ```
4. Develop the frontend against the new types (`pnpm dev`)
5. Build and commit as in the UI-only workflow above, including the updated `openapi.json` and `generated.ts`

## Key Differences from Before

| Task | Before | Now |
|------|--------|----|
| Where frontend code lives | `src/inspect_scout/_view/www/` in this repo | Separate repo, mounted at `src/inspect_scout/_view/frontend/` via submodule |
| Cloning for frontend work | `git clone` | `git clone --recurse-submodules` (or `git submodule update --init` after clone) |
| After `git pull` | Everything up to date | Run `git submodule update` (or set `submodule.recurse true`) |
| Building | `pnpm build` outputs to local `dist/` | `pnpm build` detects the Python repo and outputs to `src/inspect_scout/_view/dist/` |
| Committing frontend changes | `git add` the changed files | `git add` both `dist/` and the submodule pointer |
| CI frontend checks | All in this repo's CI | Lint/typecheck/test run in the TS monorepo's CI; this repo's CI validates `dist/`, `openapi.json`, and `generated.ts` are in sync |

## Git Commands Reference

All commands run from the Python repo root.

```bash
# Initialize the submodule (once)
git submodule update --init

# Update submodule after git pull
git submodule update

# Check which commit the submodule points to
git submodule status

# Advance submodule to latest upstream commit
git -C src/inspect_scout/_view/frontend pull

# Run any git command in the submodule without cd-ing
git -C src/inspect_scout/_view/frontend status
git -C src/inspect_scout/_view/frontend log --oneline -5

# Auto-update submodule on pull (set once)
git config submodule.recurse true
```

## FAQ / Troubleshooting

**Q: I pulled but the frontend looks stale or broken.**

You probably need to update the submodule working tree:

```bash
git submodule update
```

If you want this to happen automatically, set `git config submodule.recurse true`.

**Q: The submodule is in "detached HEAD" state — is that normal?**

Yes. The Python repo pins the submodule to a specific commit. When you run `git submodule update`, it checks out that exact commit, which results in a detached HEAD. To do development work, create a branch inside the submodule first.

**Q: How do I check if my submodule is out of sync?**

```bash
git submodule status
```

A `+` prefix means the submodule working tree is at a different commit than what the Python repo expects.

**Q: CI says `dist/` is mismatched — what do I do?**

Rebuild from the submodule and commit the result:

```bash
cd src/inspect_scout/_view/frontend
pnpm install
pnpm build
cd ../../../..
git add src/inspect_scout/_view/dist/
git commit -m "Rebuild dist"
```

**Q: CI says `openapi.json` is mismatched — what do I do?**

Re-export the schema from the Python API:

```bash
.venv/bin/python scripts/export_openapi_schema.py
git add src/inspect_scout/_view/www/openapi.json
git commit -m "Re-export openapi.json"
```

**Q: CI says `generated.ts` is mismatched — what do I do?**

Regenerate types from the committed `openapi.json`:

```bash
cd src/inspect_scout/_view/frontend
pnpm types:generate
```

Then commit the updated `generated.ts` in the TS monorepo.
