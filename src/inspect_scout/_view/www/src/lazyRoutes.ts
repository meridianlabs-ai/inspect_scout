/**
 * Lazy-loaded route components and prefetch hook.
 *
 * `routeImports` is the single source of truth: each entry is a thunk wrapping
 * a dynamic `import()`. The lazy components call the same thunks, and
 * {@link usePrefetchRoutes} fires them all on browser idle so that navigations
 * resolve instantly from the module cache.
 */
import { lazy, useEffect } from "react";

const routeImports = [
  () => import("./app/scans/ScansPanel"),
  () => import("./app/scan/ScanPanel"),
  () => import("./app/scannerResult/ScannerResultPanel"),
  () => import("./app/transcripts/TranscriptsPanel"),
  () => import("./app/transcript/TranscriptPanel"),
  () => import("./app/project/ProjectPanel"),
  () => import("./app/validation/ValidationPanel"),
  () => import("./app/runScan/RunScanPanel"),
  () => import("./app/timeline/TimelinePanel"),
] as const;

/** Lazy wrapper for {@link import("./app/scans/ScansPanel").ScansPanel}. */
export const ScansPanel = lazy(() =>
  routeImports[0]().then((m) => ({ default: m.ScansPanel }))
);
/** Lazy wrapper for {@link import("./app/scan/ScanPanel").ScanPanel}. */
export const ScanPanel = lazy(() =>
  routeImports[1]().then((m) => ({ default: m.ScanPanel }))
);
/** Lazy wrapper for {@link import("./app/scannerResult/ScannerResultPanel").ScannerResultPanel}. */
export const ScannerResultPanel = lazy(() =>
  routeImports[2]().then((m) => ({ default: m.ScannerResultPanel }))
);
/** Lazy wrapper for {@link import("./app/transcripts/TranscriptsPanel").TranscriptsPanel}. */
export const TranscriptsPanel = lazy(() =>
  routeImports[3]().then((m) => ({ default: m.TranscriptsPanel }))
);
/** Lazy wrapper for {@link import("./app/transcript/TranscriptPanel").TranscriptPanel}. */
export const TranscriptPanel = lazy(() =>
  routeImports[4]().then((m) => ({ default: m.TranscriptPanel }))
);
/** Lazy wrapper for {@link import("./app/project/ProjectPanel").ProjectPanel}. */
export const ProjectPanel = lazy(() =>
  routeImports[5]().then((m) => ({ default: m.ProjectPanel }))
);
/** Lazy wrapper for {@link import("./app/validation/ValidationPanel").ValidationPanel}. */
export const ValidationPanel = lazy(() =>
  routeImports[6]().then((m) => ({ default: m.ValidationPanel }))
);
/** Lazy wrapper for {@link import("./app/runScan/RunScanPanel").RunScanPanel}. */
export const RunScanPanel = lazy(() =>
  routeImports[7]().then((m) => ({ default: m.RunScanPanel }))
);
/** Lazy wrapper for {@link import("./app/timeline/TimelinePanel").TimelinePanel}. */
export const TimelinePanel = lazy(() =>
  routeImports[8]().then((m) => ({ default: m.TimelinePanel }))
);

/**
 * Prefetches all lazy route chunks on browser idle.
 *
 * Call once in the root layout component. Uses `requestIdleCallback` to avoid
 * competing with the initial render, then fires every `routeImports` loader in
 * parallel. Because the module loader deduplicates by specifier, any chunk
 * already loaded (the current route) resolves immediately as a no-op.
 */
export const usePrefetchRoutes = () => {
  useEffect(() => {
    requestIdleCallback(() => {
      routeImports.forEach((load) => void load());
    });
  }, []);
};
