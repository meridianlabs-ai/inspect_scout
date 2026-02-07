# Enabling Build Optimizations with Git LFS

> Companion to [Frontend Separation Plan](monorepo.md). The core proposal works without Git LFS — it uses the same "build and commit `dist/`" workflow as today. LFS is an optional enhancement that makes it practical to commit fully optimized (minified, tree-shaken, content-hashed) build output.

## Problem

1. **Built `dist/` is committed to git unminified and un-tree-shaken** — minified code produces massive opaque diffs that bloat the repo, so optimizations are disabled to keep diffs reviewable
2. **`NoCacheStaticFiles` hack** (in `inspect_scout`) disables caching to work around missing asset fingerprinting

## Why LFS

Git LFS stores file content externally while committing lightweight pointer files (~130 bytes) to git. This makes it practical to commit fully optimized build output — minified, tree-shaken, and content-hashed — without bloating the repo. Combined with asset fingerprinting (content-hashed filenames), this also eliminates the `NoCacheStaticFiles` workaround.

## Asset Fingerprinting

Current Vite config produces non-hashed filenames:

```javascript
output: {
  entryFileNames: `assets/index.js`,      // No hash
  chunkFileNames: `assets/[name].js`,     // No hash
  assetFileNames: `assets/[name].[ext]`,  // No hash
}
```

Result: Browsers cache `index.js`, serve stale versions after upgrades. The current workaround is `NoCacheStaticFiles` in [server.py](../../src/inspect_scout/_view/server.py), which disables caching for all JS files.

With LFS, content hashes become practical:

```javascript
output: {
  entryFileNames: `assets/[name]-[hash].js`,
  chunkFileNames: `assets/[name]-[hash].js`,
  assetFileNames: `assets/[name]-[hash].[ext]`,
}
```

Then remove `NoCacheStaticFiles` and use standard `StaticFiles`. Each build produces unique filenames based on content, `index.html` references them, browsers cache forever (files are immutable), and new deployments produce new URLs — no stale cache.

## LFS Configuration

The Python repo's `.gitattributes` declares LFS tracking for the build output:

```
src/inspect_scout/_view/dist/** filter=lfs diff=lfs merge=lfs -text
```

## How LFS Works

- **On commit:** Git replaces the file content with a small pointer file (~130 bytes). The actual content is stored as an LFS object.
- **On clone/checkout:** Git LFS automatically downloads the objects and replaces the pointers with the real files. This is transparent to the user.
- **On push:** LFS objects are uploaded to the LFS server (GitHub LFS, included with the repo).

## LFS Setup (One-Time)

Contributors need Git LFS installed:

```bash
git lfs install  # one-time, per machine
```

This is a common prerequisite and is already required by many repositories. After this, LFS operations are transparent — `git clone`, `git pull`, `git checkout` all work normally.

## Transparent Fallback for Users Without LFS

When a user clones or checks out the repo without Git LFS installed, git delivers LFS pointer files instead of the real content. The `dist/` directory will contain small text files (~130 bytes each) instead of working JavaScript and CSS.

Two mechanisms ensure this doesn't block anyone:

**Build hook (automatic).** A pip build hook runs during `pip install` (both `pip install git+https://...` and `pip install -e .`). It checks whether the files at the serving path are LFS pointer files. If so, it parses the OID and size from each pointer, calls the GitHub LFS batch API to obtain download URLs, and fetches the real files. If the files are already real content (LFS was installed, or they were placed by `pnpm build`), the hook does nothing.

LFS pointer files are easy to detect — they start with `version https://git-lfs.github.com/spec/v1` and contain an `oid sha256:...` line and a `size` line.

**Manual script (escape hatch).** A standalone script (`scripts/fetch-dist.sh`) provides the same logic for users who cloned without LFS and want the real files without running pip install. It uses `curl` and the GitHub LFS batch API.

The result: `pip install` works regardless of whether Git LFS is installed. Users with LFS get the files on clone; users without LFS get them on pip install.

## Open Topics

### LFS Bandwidth and Storage
- GitHub LFS includes 1 GB storage and 1 GB/month bandwidth on free plans. Paid plans extend this.
- Each `dist/` build is typically a few MB. Need to estimate monthly artifact volume based on expected publish frequency.
- Old LFS objects accumulate but can be pruned with `git lfs prune`.

### Artifact Immutability
- With LFS, overwriting a published `dist/` means amending or force-pushing — git's normal safeguards apply.
- Should CI enforce that `dist/` on `main` is only updated via PR (no direct pushes)?
