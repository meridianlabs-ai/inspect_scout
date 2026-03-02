/**
 * Timeline state hook.
 *
 * Provides a fully expanded, flat timeline view. All descendant spans are
 * always visible — there is no drill-down navigation. Selection is key-based,
 * using the unique tree-position key from each SwimlaneRow.
 */

import { useCallback, useMemo } from "react";
import { useSearchParams } from "react-router-dom";

import {
  type Timeline,
  type TimelineBranch,
  type TimelineSpan,
} from "../../../components/transcript/timeline";
import {
  type SwimlaneRow,
  computeFlatSwimlaneRows,
} from "../utils/swimlaneRows";

// =============================================================================
// Query Parameter Constants
// =============================================================================

const kSelectedParam = "selected";

// =============================================================================
// Types
// =============================================================================

export interface TimelineState {
  /** The root TimelineSpan (always the timeline root). */
  node: TimelineSpan;
  /** Flat swimlane rows for all descendants. */
  rows: SwimlaneRow[];
  /** Currently selected row key, or null. */
  selected: string | null;
  /** Select a row by key, or null to clear. */
  select: (key: string | null) => void;
  /** Clear the selection (returns to default root selection). */
  clearSelection: () => void;
}

// =============================================================================
// Branch Lookup (used by branch marker popover)
// =============================================================================

export interface BranchLookupResult {
  /** The span that owns the branches. */
  owner: TimelineSpan;
  /** Matching branches with their 1-indexed position. */
  branches: Array<{ branch: TimelineBranch; index: number }>;
}

/**
 * Finds all branches matching a forkedAt UUID anywhere in the span tree.
 * Returns the owning span and matching branches.
 */
export function findBranchesByForkedAt(
  node: TimelineSpan,
  forkedAt: string
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
    return { owner: node, branches: matches };
  }

  // Recurse into child spans
  for (const item of node.content) {
    if (item.type === "span") {
      const found = findBranchesByForkedAt(item, forkedAt);
      if (found) return found;
    }
  }

  return null;
}

/**
 * Creates a TimelineSpan for a branch's content (informational display).
 *
 * If the branch has exactly one child span, returns that span directly
 * (with a ↳ prefix on its name). Otherwise creates a synthetic container.
 */
export function createBranchSpan(
  branch: TimelineBranch,
  index: number
): TimelineSpan {
  const label = deriveBranchLabel(branch, index);

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
    idleTime: branch.idleTime,
  };
}

function deriveBranchLabel(branch: TimelineBranch, index: number): string {
  for (const item of branch.content) {
    if (item.type === "span") return item.name;
  }
  return `Branch ${index}`;
}

// =============================================================================
// Hook
// =============================================================================

/**
 * Timeline state hook.
 *
 * Computes a fully expanded flat list of swimlane rows from the timeline root.
 * Selection is driven by the `selected` URL search param using row keys.
 */
export function useTimeline(timeline: Timeline): TimelineState {
  const [searchParams, setSearchParams] = useSearchParams();

  const selectedParam = searchParams.get(kSelectedParam) ?? null;

  // Always use the root node
  const node = timeline.root;

  // Compute flat swimlane rows for the entire tree
  const rows = useMemo(() => computeFlatSwimlaneRows(node), [node]);

  // Default selection: explicit param > root row key
  const selected = useMemo(() => {
    if (selectedParam !== null) return selectedParam;
    return rows[0]?.key ?? null;
  }, [selectedParam, rows]);

  const select = useCallback(
    (key: string | null) => {
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          if (key) {
            next.set(kSelectedParam, key);
          } else {
            next.delete(kSelectedParam);
          }
          next.delete("event");
          next.delete("message");
          return next;
        },
        { replace: true }
      );
    },
    [setSearchParams]
  );

  const clearSelection = useCallback(() => {
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        next.delete(kSelectedParam);
        next.delete("event");
        next.delete("message");
        return next;
      },
      { replace: true }
    );
  }, [setSearchParams]);

  return {
    node,
    rows,
    selected,
    select,
    clearSelection,
  };
}
