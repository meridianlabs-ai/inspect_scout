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

### Runtime resolution with a cache directory

`scout view` resolves dist files **at startup**, using a cache directory (`~/.cache/inspect_scout/dist/`) that is entirely outside the working tree. The repo's `dist/` is never modified, so `git pull` always works cleanly.

**On startup, the server determines what to serve:**

1. **In-repo `dist/` contains real files** (LFS installed, or local dev `pnpm build`) → serve directly from the repo. Cache not involved.
2. **In-repo `dist/` contains LFS pointer files** → serve from the cache directory, downloading if needed.

**How the cache works:**

LFS pointer files are easy to detect — they start with `version https://git-lfs.github.com/spec/v1` and contain an `oid sha256:...` line and a `size` line. The SHA-256 OID is a content hash, which serves as a natural cache key.

When `dist/` contains pointers:
- Parse the OID from each pointer file
- Compare against what's in the cache
- **Cache hit** (OIDs match) → serve from cache, no download
- **Cache miss** (new OIDs, or empty cache) → call the GitHub LFS batch API, download the real files into the cache, then serve

**LFS batch API download protocol (verified):**

The GitHub LFS batch API allows anonymous downloads from public repos — no authentication required. The protocol is:

1. **Parse pointer files.** Each pointer is a small text file:
   ```
   version https://git-lfs.github.com/spec/v1
   oid sha256:<64-char-hex>
   size <bytes>
   ```

2. **POST to the batch endpoint** at `https://github.com/{owner}/{repo}.git/info/lfs/objects/batch`:
   ```json
   {
     "operation": "download",
     "transfers": ["basic"],
     "objects": [
       { "oid": "<sha256-hex>", "size": <bytes> }
     ]
   }
   ```
   With headers:
   - `Content-Type: application/vnd.git-lfs+json`
   - `Accept: application/vnd.git-lfs+json`

   Multiple objects can be batched in a single request.

3. **Response** contains a pre-signed S3 URL per object:
   ```json
   {
     "objects": [{
       "oid": "...",
       "size": 620773,
       "actions": {
         "download": {
           "href": "https://github-cloud.githubusercontent.com/alambic/media/...",
           "expires_at": "2026-02-19T00:10:28Z",
           "expires_in": 3600
         }
       }
     }]
   }
   ```

4. **Download** from the `href` URL. Verify the downloaded file's SHA-256 matches the OID.

Tested against `Schoonology/git-lfs-test` (public repo) — anonymous batch API request returned a valid pre-signed URL, downloaded content matched the declared size (620,773 bytes) and SHA-256 OID exactly.

This handles every scenario:

| Scenario | What happens |
|----------|-------------|
| LFS installed, clone/pull worked normally | Real files in repo → serve directly |
| Local dev, `pnpm build` output | Real files in repo → serve directly |
| No LFS, fresh clone | Pointers in repo → cache miss → download → serve from cache |
| No LFS, `git pull` brings new dist | New pointers in repo → OIDs change → cache miss → re-download |
| No LFS, `git pull`, no dist changes | Same pointers → OIDs match → cache hit → serve from cache |
| `dist/` missing entirely | Error with helpful message |

**Key properties:**
- The working tree is never modified — `git status` stays clean, `git pull` always works
- Cache is keyed by content hash — no invalidation logic needed, the pointers themselves declare freshness
- First launch (or first launch after an update) has a one-time download delay of a few seconds, with a clear progress message

**Manual script (escape hatch).** A standalone script (`scripts/fetch-dist.sh`) provides the same download logic for users who want the real files outside of `scout view`. It uses `curl` and the GitHub LFS batch API, writing to the same cache directory.

## Open Topics

### LFS Bandwidth and Storage
- GitHub LFS includes 1 GB storage and 1 GB/month bandwidth on free plans. Paid plans extend this.
- Each `dist/` build is typically a few MB. Need to estimate monthly artifact volume based on expected publish frequency.
- Old LFS objects accumulate but can be pruned with `git lfs prune`.

### Artifact Immutability
- With LFS, overwriting a published `dist/` means amending or force-pushing — git's normal safeguards apply.
- Should CI enforce that `dist/` on `main` is only updated via PR (no direct pushes)?
