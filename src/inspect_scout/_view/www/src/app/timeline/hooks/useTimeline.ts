/**
 * Timeline navigation hook and pure helper functions.
 *
 * Provides URL-driven drill-down navigation through the timeline span tree.
 * Pure functions (parsePathSegment, resolvePath, buildBreadcrumbs) are exported
 * for unit testing without DOM dependencies.
 */

import { useCallback, useMemo } from "react";
import { useSearchParams } from "react-router-dom";

import type {
  Timeline,
  TimelineBranch,
  TimelineSpan,
} from "../../../components/transcript/timeline";
import {
  type SwimlaneRow,
  compareByTime,
  computeSwimlaneRows,
} from "../utils/swimlaneRows";

// =============================================================================
// Query Parameter Constants
// =============================================================================

const kPathParam = "path";
const kSelectedParam = "selected";

// =============================================================================
// Types
// =============================================================================

export interface BreadcrumbSegment {
  label: string;
  path: string;
}

export interface TimelineState {
  /** The resolved TimelineSpan for the current path. */
  node: TimelineSpan;
  /** Swimlane rows computed from the resolved node. */
  rows: SwimlaneRow[];
  /** Breadcrumb trail from root to the current path. */
  breadcrumbs: BreadcrumbSegment[];
  /** Currently selected span identifier, or null. Encoded as "name" or "name-N". */
  selected: string | null;
  /** Navigate into a child span by name and optional span index. */
  drillDown: (name: string, spanIndex?: number) => void;
  /** Navigate up one level. */
  goUp: () => void;
  /** Navigate directly to a specific path (for breadcrumb jumps). */
  navigateTo: (path: string) => void;
  /** Set or clear the selected span. Use spanIndex for multi-span rows. */
  select: (name: string | null, spanIndex?: number) => void;
}

// =============================================================================
// Pure Functions
// =============================================================================

/**
 * Parses a single path segment into a name and optional span index.
 *
 * The span index suffix is `-N` where N is a positive integer (1-indexed).
 * Only the last `-N` suffix is considered; earlier hyphens are part of the name.
 *
 * Examples:
 *   "explore"       → { name: "explore", spanIndex: null }
 *   "explore-2"     → { name: "explore", spanIndex: 2 }
 *   "my-agent"      → { name: "my-agent", spanIndex: null }
 *   "my-agent-3"    → { name: "my-agent", spanIndex: 3 }
 *   "explore-0"     → { name: "explore-0", spanIndex: null }  (0 is not valid)
 */
export function parsePathSegment(segment: string): {
  name: string;
  spanIndex: number | null;
} {
  const match = /^(.+)-(\d+)$/.exec(segment);
  if (match) {
    const name = match[1]!;
    const index = parseInt(match[2]!, 10);
    if (index >= 1) {
      return { name, spanIndex: index };
    }
  }
  return { name: segment, spanIndex: null };
}

/**
 * Resolves a path string to a span in the timeline tree.
 *
 * Path format: slash-separated segments, e.g. "build/code/test".
 * Empty or missing path resolves to the root span.
 *
 * Span names are matched case-insensitively. The `-N` suffix selects the
 * Nth occurrence (1-indexed) among same-named children; without a suffix,
 * the first match is returned.
 *
 * Returns null if the path is invalid.
 */
export function resolvePath(
  timeline: Timeline,
  pathString: string
): TimelineSpan | null {
  if (!pathString) return timeline.root;

  const segments = pathString.split("/").filter((s) => s.length > 0);
  if (segments.length === 0) return timeline.root;

  // Walk the tree from root
  let current: TimelineSpan = timeline.root;

  for (const segment of segments) {
    const branchSpan = resolveBranchSegment(current, segment);
    if (branchSpan) {
      current = branchSpan;
      continue;
    }
    const { name, spanIndex } = parsePathSegment(segment);
    const child = findChildSpan(current, name, spanIndex);
    if (!child) return null;
    current = child;
  }

  return current;
}

/**
 * Builds a breadcrumb trail for the given path.
 *
 * Always starts with a "Root" breadcrumb at path "". Each subsequent segment
 * appends to the path. Labels use the resolved span's display name when
 * available, otherwise the raw segment.
 */
export function buildBreadcrumbs(
  pathString: string,
  timeline: Timeline
): BreadcrumbSegment[] {
  const crumbs: BreadcrumbSegment[] = [{ label: timeline.root.name, path: "" }];

  if (!pathString) return crumbs;

  const segments = pathString.split("/").filter((s) => s.length > 0);
  let current: TimelineSpan | null = timeline.root;

  for (let i = 0; i < segments.length; i++) {
    const segment = segments[i]!;
    const path = segments.slice(0, i + 1).join("/");

    if (current) {
      // Try branch segment first (e.g. "@branch-1")
      const branchSpan = resolveBranchSegment(current, segment);
      if (branchSpan) {
        crumbs.push({ label: branchSpan.name, path });
        current = branchSpan;
      } else {
        const { name, spanIndex } = parsePathSegment(segment);
        const child = findChildSpan(current, name, spanIndex);
        if (child) {
          crumbs.push({ label: child.name, path });
          current = child;
        } else {
          crumbs.push({ label: segment, path });
          current = null;
        }
      }
    } else {
      crumbs.push({ label: segment, path });
    }
  }

  return crumbs;
}

// =============================================================================
// Internal Helpers
// =============================================================================

/**
 * Finds a child span by name (case-insensitive) and optional span index.
 *
 * When spanIndex is null and there's exactly one match, returns it directly.
 * When spanIndex is null and there are multiple matches (parallel group),
 * returns a synthetic container span wrapping all matches as numbered children.
 * When spanIndex is N, returns the Nth same-named child (1-indexed).
 */
function findChildSpan(
  parent: TimelineSpan,
  name: string,
  spanIndex: number | null
): TimelineSpan | null {
  const lowerName = name.toLowerCase();
  const matches: TimelineSpan[] = [];

  for (const item of parent.content) {
    if (item.type === "span" && item.name.toLowerCase() === lowerName) {
      matches.push(item);
    }
  }

  if (matches.length === 0) return null;

  // Specific index requested → return that occurrence
  if (spanIndex !== null) {
    return matches[spanIndex - 1] ?? null;
  }

  // Single match → return it directly
  if (matches.length === 1) {
    return matches[0]!;
  }

  // Multiple matches (parallel group) → create a synthetic container
  // with numbered children (e.g., "Explore 1", "Explore 2", "Explore 3")
  return createParallelContainer(matches);
}

/**
 * Creates a synthetic TimelineSpan that wraps parallel agents as children.
 * Each child is renamed with a 1-based index suffix (e.g., "Explore 1").
 * The container's time range is the envelope of all agents, and tokens are summed.
 */
function createParallelContainer(agents: TimelineSpan[]): TimelineSpan {
  const displayName = agents[0]!.name;
  const startTime = agents.reduce(
    (min, a) => (a.startTime.getTime() < min.getTime() ? a.startTime : min),
    agents[0]!.startTime
  );
  const endTime = agents.reduce(
    (max, a) => (a.endTime.getTime() > max.getTime() ? a.endTime : max),
    agents[0]!.endTime
  );
  const totalTokens = agents.reduce((sum, a) => sum + a.totalTokens, 0);

  // Sort by start time (end time as tiebreaker), then number sequentially
  const sorted = [...agents].sort(compareByTime);
  const numberedAgents: TimelineSpan[] = sorted.map((agent, i) => ({
    ...agent,
    name: `${displayName} ${i + 1}`,
  }));

  return {
    type: "span",
    id: `parallel-${displayName.toLowerCase()}`,
    name: displayName,
    spanType: "agent",
    content: numberedAgents,
    branches: [],
    utility: false,
    startTime,
    endTime,
    totalTokens,
  };
}

// =============================================================================
// Branch Resolution
// =============================================================================

const BRANCH_PREFIX = "@branch-";

/**
 * Parses a `@branch-N` path segment and resolves it to a synthetic span.
 *
 * Returns null if the segment is not a branch segment or the index is invalid.
 * N is 1-indexed into the parent's branches array.
 */
function resolveBranchSegment(
  parent: TimelineSpan,
  segment: string
): TimelineSpan | null {
  if (!segment.startsWith(BRANCH_PREFIX)) return null;

  const indexStr = segment.slice(BRANCH_PREFIX.length);
  const index = parseInt(indexStr, 10);
  if (isNaN(index) || index < 1) return null;

  const branch = parent.branches[index - 1];
  if (!branch) return null;

  return createBranchSpan(branch, index);
}

/**
 * Creates a TimelineSpan for a branch's content.
 *
 * If the branch has exactly one child span, returns that span directly
 * (with a ↳ prefix on its name) to avoid a redundant wrapper level.
 * Otherwise creates a synthetic container wrapping all branch content.
 */
export function createBranchSpan(
  branch: TimelineBranch,
  index: number
): TimelineSpan {
  const label = deriveBranchLabel(branch, index);

  // If exactly one child span, return it directly with ↳ prefix
  const childSpans = branch.content.filter(
    (item): item is TimelineSpan => item.type === "span"
  );
  if (childSpans.length === 1) {
    return {
      ...childSpans[0]!,
      name: `\u21B3 ${childSpans[0]!.name}`,
    };
  }

  return {
    type: "span",
    id: `branch-${branch.forkedAt}-${index}`,
    name: `\u21B3 ${label}`,
    spanType: "branch",
    content: branch.content,
    branches: [],
    utility: false,
    startTime: branch.startTime,
    endTime: branch.endTime,
    totalTokens: branch.totalTokens,
  };
}

/**
 * Derives a display label for a branch.
 *
 * Uses the name of the first child span if one exists, otherwise "Branch N".
 */
function deriveBranchLabel(branch: TimelineBranch, index: number): string {
  for (const item of branch.content) {
    if (item.type === "span") return item.name;
  }
  return `Branch ${index}`;
}

// =============================================================================
// Branch Lookup
// =============================================================================

export interface BranchLookupResult {
  /** The span that owns the branches. */
  owner: TimelineSpan;
  /** Path segments from the search root to the owner (empty if owner is root). */
  ownerPath: string[];
  /** Matching branches with their 1-indexed position. */
  branches: Array<{ branch: TimelineBranch; index: number }>;
}

/**
 * Finds all branches matching a forkedAt UUID anywhere in the span tree.
 * Returns the owning span, its path from root, and matching branches.
 */
export function findBranchesByForkedAt(
  node: TimelineSpan,
  forkedAt: string,
  pathSoFar: string[] = []
): BranchLookupResult | null {
  // Check this node's branches
  const matches: Array<{ branch: TimelineBranch; index: number }> = [];
  for (let i = 0; i < node.branches.length; i++) {
    const branch = node.branches[i]!;
    if (branch.forkedAt === forkedAt) {
      matches.push({ branch, index: i + 1 });
    }
  }
  if (matches.length > 0) {
    return { owner: node, ownerPath: pathSoFar, branches: matches };
  }

  // Recurse into child spans
  for (const item of node.content) {
    if (item.type === "span") {
      const found = findBranchesByForkedAt(item, forkedAt, [
        ...pathSoFar,
        item.name.toLowerCase(),
      ]);
      if (found) return found;
    }
  }

  return null;
}

// =============================================================================
// Hook
// =============================================================================

/**
 * Timeline navigation hook.
 *
 * Reads `path` and `selected` from URL search params. Returns the resolved
 * node, computed swimlane rows, breadcrumbs, and navigation functions.
 *
 * All navigation updates the URL via search param replacement, preserving
 * other search params.
 */
export function useTimeline(timeline: Timeline): TimelineState {
  const [searchParams, setSearchParams] = useSearchParams();

  const pathString = searchParams.get(kPathParam) ?? "";
  const selectedParam = searchParams.get(kSelectedParam) ?? null;

  // Resolve the current path to a span
  const resolved = useMemo(
    () => resolvePath(timeline, pathString),
    [timeline, pathString]
  );

  // Fall back to root if path resolution fails
  const node = useMemo(() => resolved ?? timeline.root, [timeline, resolved]);

  // Compute swimlane rows
  const rows = useMemo(() => computeSwimlaneRows(node), [node]);

  // Default selection: explicit param > first child for parallel containers > root
  const selected = useMemo(() => {
    if (selectedParam !== null) return selectedParam;
    if (node.id.startsWith("parallel-") && rows.length > 1) {
      return rows[1]!.name;
    }
    return rows[0]?.name ?? null;
  }, [selectedParam, node.id, rows]);

  // Build breadcrumbs
  const breadcrumbs = useMemo(
    () => buildBreadcrumbs(pathString, timeline),
    [pathString, timeline]
  );

  // Navigation functions
  const drillDown = useCallback(
    (name: string, spanIndex?: number) => {
      const segment = spanIndex ? `${name}-${spanIndex}` : name;
      const newPath = pathString ? `${pathString}/${segment}` : segment;
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          next.set(kPathParam, newPath);
          next.delete(kSelectedParam);
          return next;
        },
        { replace: true }
      );
    },
    [pathString, setSearchParams]
  );

  const goUp = useCallback(() => {
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        if (pathString) {
          const segments = pathString.split("/");
          segments.pop();
          const newPath = segments.join("/");
          if (newPath) {
            next.set(kPathParam, newPath);
          } else {
            next.delete(kPathParam);
          }
        }
        next.delete(kSelectedParam);
        return next;
      },
      { replace: true }
    );
  }, [pathString, setSearchParams]);

  const navigateTo = useCallback(
    (path: string) => {
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          if (path) {
            next.set(kPathParam, path);
          } else {
            next.delete(kPathParam);
          }
          next.delete(kSelectedParam);
          return next;
        },
        { replace: true }
      );
    },
    [setSearchParams]
  );

  const select = useCallback(
    (name: string | null, spanIndex?: number) => {
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          if (name) {
            const value = spanIndex ? `${name}-${spanIndex}` : name;
            next.set(kSelectedParam, value);
          } else {
            next.delete(kSelectedParam);
          }
          return next;
        },
        { replace: true }
      );
    },
    [setSearchParams]
  );

  return {
    node,
    rows,
    breadcrumbs,
    selected,
    drillDown,
    goUp,
    navigateTo,
    select,
  };
}
