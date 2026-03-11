# Migration Notes

Instructions for getting the `mono` branch ready to merge to `main`.

## Related docs

- [Frontend submodule guide](guides/frontend-submodule.md) — submodule workflow for ongoing development
- [Walkthrough: coordinated API + UI changes](design/plans/walkthrough-api-change.md)
- [Walkthrough: UI-only changes](design/plans/walkthrough-ui-only.md)

## 1. Fresh source copy from www → ts-mono

Re-copy source from `www/` into ts-mono. The `www/` directory was deleted on
the `mono` branch but still exists on `main` — you'll need to grab it from
there (e.g., check out `www/` from main temporarily, or use
`git show main:src/inspect_scout/_view/www/src/...`).

For each file, overwrite the entire contents with the www version. The only
changes made to existing ts-mono source files were import rewrites<sup>*</sup> — no logic
changes — so a full overwrite is safe. You'll redo the import rewrites
afterward (see "Fix imports after copy" below).

<sup>*</sup> The only exceptions are the Build-time globals mentioned below.

### What goes where

Everything under `www/src/` goes to `apps/scout/src/`, **except**:

- `www/src/utils/` → `packages/util/`
- `www/src/hooks/` → `packages/react/hooks/`
- `www/src/components/StickyScroll.tsx` → `packages/react/components/`

The ts-mono directories are already populated with the previous copy — use
them as a reference for the expected structure. No new splitting decisions
should be needed.

### What NOT to copy

Do not overwrite project-level configuration in ts-mono:

- `package.json`, `tsconfig.json`, `tsconfig.*.json`
- ESLint configs, Prettier configs, `.prettierignore`
- `turbo.json`, `pnpm-workspace.yaml`
- Any other tooling/config files

If www has **new configuration** that doesn't exist in ts-mono, flag it for
discussion rather than copying it over.

If www has **new dependencies**, add them to the appropriate ts-mono
`package.json` manually rather than overwriting the file.

### Fix imports after copy

Relative imports that pointed to shared code in www need to become workspace
package imports. Use global search & replace for patterns like:

```
from "../../utils/xxx"  →  from "@tsmono/util"
from "../../hooks/xxx"  →  from "@tsmono/react/hooks/xxx"  (or whatever the barrel exports)
```

Note: `@tsmono/util` uses barrel exports — import from the package, not
individual files.

### Validate cross-package dependencies

After updating imports, run `pnpm manypkg check` to verify that workspace
`package.json` files correctly declare their cross-monorepo dependencies.
For example, if `apps/scout` now imports from `@tsmono/util`, it must list
`@tsmono/util` in its `dependencies`. `pnpm manypkg fix` can auto-fix most
issues.

### Build-time globals — needs discussion

Vite `define` globals (`__DEV_WATCH__`, `__LOGGING_FILTER__`,
`__SCOUT_RUN_SCAN__`, etc.) throw `ReferenceError` in non-Vite contexts
(tests, SSR, Node scripts) when code moves to shared packages — vitest only
applies `define` substitutions within the project root.

> The current state is a minimal "make it build" fix, not a considered design.
> The `typeof` guard approach works but may not be the right long-term answer
> (e.g., maybe these should be environment variables, a shared config module,
> or vitest `define` config in shared packages). **We should discuss this**

Current state:

- `packages/util/src/logger.ts` — has `typeof` guards for `__DEV_WATCH__`
  and `__LOGGING_FILTER__`:
  ```ts
  const isDevWatch = typeof __DEV_WATCH__ !== "undefined" && __DEV_WATCH__;
  const loggingFilter =
    typeof __LOGGING_FILTER__ !== "undefined" ? __LOGGING_FILTER__ : "*";
  ```
- `apps/scout/src/router/activities.tsx` — bare `declare const` with no
  guard. Lives in the app (not a shared package) so only breaks if tests
  import it without Vite's `define` substitution.
- `apps/scout/vite.config.ts` — defines all three globals.

After the fresh copy, audit all files in shared packages for `declare const`
/ `define` patterns — any global injected by `vite.config.ts` needs
handling.

## 2. Verify everything works

Run the full suite after the copy + import rewrites:

```bash
cd src/inspect_scout/_view/ts-mono

pnpm install
pnpm check          # typecheck + lint
pnpm build          # production build (outputs to _view/dist/)
pnpm test           # unit/integration tests
```

Then smoke test manually:

```bash
scout view           # verify the built frontend loads and works
```

## 3. Validate CI

CI hasn't been tested in a while. Run the equivalent checks locally before
pushing:

- **Python checks**: `make check && make test` (from repo root)
- **OpenAPI schema sync**: `.venv/bin/python scripts/export_openapi_schema.py`
  then verify `_view/openapi.json` is unchanged
- **generated.ts sync**: `pnpm --filter scout types:generate` then verify
  `generated.ts` is unchanged
- **dist/ sync**: `pnpm build` then verify `_view/dist/` matches what's committed

Push the branch and confirm all CI jobs pass on the PR.

## 4. Validate npm publishing

The `npm-publish.yml` workflow moved from the Python repo to the ts-mono repo.
Verify it works:

1. Check that the ts-mono GitHub repo has the npm environment and secrets
   configured. If not, flag for setup.
2. Do a dry-run publish to confirm the workflow works end-to-end.

## 5. ~~Clean up temporary files~~ DONE

Before merging `mono` → `main`:

- **Delete** temporary planning files in `design/plans/`:
  - `monorepo.md` — delete (migration plan, served its purpose). Salvage any
    content worth keeping into a permanent location first.
  - `walkthrough-api-change.md` — decide: keep, move, or delete
  - `walkthrough-ui-only.md` — decide: keep, move, or delete
- **Migrate** anything worth preserving long-term into a permanent location
  (e.g., a design doc in `design/`).

## Reference: tooling notes

### Preserve `.prettierignore` files when updating source

When pulling in new source from upstream, do not overwrite the `.prettierignore`
files. Each app/package may have its own `.prettierignore` for its local
`pnpm format` script, and the root `.prettierignore` covers the repo-wide
`pnpm format`. Merge any new ignore entries rather than replacing the files.
