/**
 * Timeline navigation hook and pure helper functions.
 *
 * Provides URL-driven drill-down navigation through the transcript node tree.
 * Pure functions (parsePathSegment, resolvePath, buildBreadcrumbs) are exported
 * for unit testing without DOM dependencies.
 */

import { useCallback, useMemo } from "react";
import { useSearchParams } from "react-router-dom";

import type {
  AgentNode,
  SectionNode,
  TranscriptNodes,
} from "../../components/transcript/nodes";

import {
  type SwimLaneRow,
  computeSwimLaneRows,
  sectionToAgent,
} from "./swimlaneRows";

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
  /** The resolved AgentNode for the current path. */
  node: AgentNode;
  /** Swimlane rows computed from the resolved node. */
  rows: SwimLaneRow[];
  /** Breadcrumb trail from root to the current path. */
  breadcrumbs: BreadcrumbSegment[];
  /** Currently selected row name, or null. */
  selected: string | null;
  /** Navigate into a child agent by name and optional span index. */
  drillDown: (name: string, spanIndex?: number) => void;
  /** Navigate up one level. */
  goUp: () => void;
  /** Set or clear the selected row. */
  select: (name: string | null) => void;
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
 * Resolves a path string to a node in the transcript tree.
 *
 * Path format: slash-separated segments, e.g. "build/code/test".
 * Empty or missing path resolves to the root agent.
 *
 * Special segment names (case-insensitive, first segment only):
 *   - "init"    → tree.init
 *   - "scoring" → tree.scoring
 *
 * Agent names are matched case-insensitively. The `-N` suffix selects the
 * Nth occurrence (1-indexed) among same-named children; without a suffix,
 * the first match is returned.
 *
 * Returns null if the tree has no agent or the path is invalid.
 */
export function resolvePath(
  tree: TranscriptNodes,
  pathString: string
): AgentNode | SectionNode | null {
  if (!tree.agent) return null;

  if (!pathString) return tree.agent;

  const segments = pathString.split("/").filter((s) => s.length > 0);
  if (segments.length === 0) return tree.agent;

  // Check for special first-segment names
  const firstSegment = segments[0]!.toLowerCase();
  if (firstSegment === "init") {
    return tree.init;
  }
  if (firstSegment === "scoring") {
    return tree.scoring;
  }

  // Walk the tree from root agent
  let current: AgentNode = tree.agent;

  for (const segment of segments) {
    const { name, spanIndex } = parsePathSegment(segment);
    const child = findChildAgent(current, name, spanIndex);
    if (!child) return null;
    current = child;
  }

  return current;
}

/**
 * Builds a breadcrumb trail for the given path.
 *
 * Always starts with a "Root" breadcrumb at path "". Each subsequent segment
 * appends to the path. Labels use the resolved agent's display name when
 * available, otherwise the raw segment.
 */
export function buildBreadcrumbs(
  pathString: string,
  tree: TranscriptNodes
): BreadcrumbSegment[] {
  const rootLabel = tree.agent?.name ?? "Root";
  const crumbs: BreadcrumbSegment[] = [{ label: rootLabel, path: "" }];

  if (!pathString || !tree.agent) return crumbs;

  const segments = pathString.split("/").filter((s) => s.length > 0);
  let current: AgentNode | null = tree.agent;

  for (let i = 0; i < segments.length; i++) {
    const segment = segments[i]!;
    const path = segments.slice(0, i + 1).join("/");

    if (current) {
      const { name, spanIndex } = parsePathSegment(segment);

      // Check for special names at the first segment
      if (i === 0) {
        const lower = name.toLowerCase();
        if (lower === "init") {
          crumbs.push({ label: "Init", path });
          current = null;
          continue;
        }
        if (lower === "scoring") {
          crumbs.push({ label: "Scoring", path });
          current = null;
          continue;
        }
      }

      const child = findChildAgent(current, name, spanIndex);
      if (child) {
        crumbs.push({ label: child.name, path });
        current = child;
      } else {
        crumbs.push({ label: segment, path });
        current = null;
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
 * Finds a child agent by name (case-insensitive) and optional span index.
 *
 * When spanIndex is null, returns the first match.
 * When spanIndex is N, returns the Nth same-named child (1-indexed).
 */
function findChildAgent(
  parent: AgentNode,
  name: string,
  spanIndex: number | null
): AgentNode | null {
  const lowerName = name.toLowerCase();
  let matchCount = 0;

  for (const item of parent.content) {
    if (item.type === "agent" && item.name.toLowerCase() === lowerName) {
      matchCount++;
      if (spanIndex === null || matchCount === spanIndex) {
        return item;
      }
    }
  }

  return null;
}

/**
 * Prepares the root AgentNode for swimlane computation.
 *
 * At the root level, init and scoring sections are folded into the agent's
 * content as AgentNodes (via sectionToAgent) so they appear as swimlane rows.
 */
function prepareRootNode(tree: TranscriptNodes): AgentNode {
  const agent = tree.agent;
  if (!agent) {
    throw new Error("Cannot prepare root node: tree has no agent");
  }

  const extraContent: AgentNode[] = [];
  if (tree.init) {
    extraContent.push(sectionToAgent(tree.init));
  }
  if (tree.scoring) {
    extraContent.push(sectionToAgent(tree.scoring));
  }

  if (extraContent.length === 0) return agent;

  // Create a shallow copy with init/scoring folded in
  return {
    ...agent,
    content: [...agent.content, ...extraContent],
  };
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
export function useTimeline(tree: TranscriptNodes): TimelineState {
  const [searchParams, setSearchParams] = useSearchParams();

  const pathString = searchParams.get(kPathParam) ?? "";
  const selected = searchParams.get(kSelectedParam) ?? null;

  // Resolve the current path to a node
  const resolved = useMemo(
    () => resolvePath(tree, pathString),
    [tree, pathString]
  );

  // Convert SectionNode to AgentNode, or use agent directly
  // Fall back to root if path resolution fails
  const node = useMemo(() => {
    if (!tree.agent) {
      throw new Error("useTimeline requires a tree with an agent");
    }

    if (!resolved) {
      // Invalid path — fall back to root
      return prepareRootNode(tree);
    }

    if (resolved.type === "section") {
      return sectionToAgent(resolved);
    }

    // At root level, fold in init/scoring
    if (!pathString) {
      return prepareRootNode(tree);
    }

    return resolved;
  }, [tree, resolved, pathString]);

  // Compute swimlane rows
  const rows = useMemo(() => computeSwimLaneRows(node), [node]);

  // Build breadcrumbs
  const breadcrumbs = useMemo(
    () => buildBreadcrumbs(pathString, tree),
    [pathString, tree]
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

  const select = useCallback(
    (name: string | null) => {
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          if (name) {
            next.set(kSelectedParam, name);
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

  return { node, rows, breadcrumbs, selected, drillDown, goUp, select };
}
