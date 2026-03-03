/**
 * Swimlane row computation for the timeline UI.
 *
 * Transforms a TimelineSpan's children into SwimlaneRow[] for rendering
 * as horizontal swimlane bars. Handles sequential, iterative (multiple spans),
 * and parallel (overlapping) span patterns.
 */

import type { TimelineSpan } from "../../../components/transcript/timeline";

// =============================================================================
// Sorting
// =============================================================================

/** Compare spans by start time, with end time as tiebreaker. */
export function compareByTime(
  a: { startTime: Date; endTime: Date },
  b: { startTime: Date; endTime: Date }
): number {
  return (
    a.startTime.getTime() - b.startTime.getTime() ||
    a.endTime.getTime() - b.endTime.getTime()
  );
}

// =============================================================================
// Types
// =============================================================================

export interface SingleSpan {
  agent: TimelineSpan;
}

export interface ParallelSpan {
  agents: TimelineSpan[];
}

export type RowSpan = SingleSpan | ParallelSpan;

export interface SwimlaneRow {
  /** Unique key encoding tree position (e.g. "transcript/build/test"). */
  key: string;
  name: string;
  /** Depth in the span tree. 0 = root, 1 = direct child, etc. */
  depth: number;
  spans: RowSpan[];
  totalTokens: number;
  startTime: Date;
  endTime: Date;
}

// =============================================================================
// Type Guards
// =============================================================================

export function isSingleSpan(span: RowSpan): span is SingleSpan {
  return "agent" in span;
}

export function isParallelSpan(span: RowSpan): span is ParallelSpan {
  return "agents" in span;
}

/** Unwrap a RowSpan to a flat array of TimelineSpan agents. */
export function getAgents(span: RowSpan): TimelineSpan[] {
  return isSingleSpan(span) ? [span.agent] : span.agents;
}

// =============================================================================
// Overlap Detection
// =============================================================================

/** Tolerance in milliseconds for considering two spans as overlapping. */
const OVERLAP_TOLERANCE_MS = 100;

// =============================================================================
// Main Computation
// =============================================================================

/**
 * Computes swimlane rows from a TimelineSpan's children.
 *
 * @returns Array of SwimlaneRow, with the parent row always first,
 *          followed by child rows ordered by earliest start time.
 */
export function computeSwimlaneRows(
  node: TimelineSpan,
  options?: { includeUtility?: boolean }
): SwimlaneRow[] {
  const includeUtility = options?.includeUtility ?? false;

  // Parent row is always first
  const parentRow = buildParentRow(node);

  // Collect child spans, optionally filtering utility agents
  const children = node.content.filter(
    (item): item is TimelineSpan =>
      item.type === "span" && (includeUtility || !item.utility)
  );

  if (children.length === 0) {
    return [parentRow];
  }

  // Group by name (case-insensitive)
  const groups = groupByName(children);

  // Build rows from groups
  const childRows: SwimlaneRow[] = [];
  for (const [displayName, spans] of groups) {
    const row = buildRowFromGroup(displayName, spans);
    if (row) {
      childRows.push(row);
    }
  }

  // Sort child rows by earliest start time
  childRows.sort(compareByTime);

  return [parentRow, ...childRows];
}

// =============================================================================
// Internal Helpers
// =============================================================================

/**
 * Partitions time-sorted spans into clusters of overlapping spans.
 *
 * Uses a sweep-line: extends the current cluster while spans overlap its
 * time range, then starts a new cluster when a gap is found.
 * Input must be sorted by start time.
 */
function partitionIntoClusters(sorted: TimelineSpan[]): TimelineSpan[][] {
  if (sorted.length === 0) return [];

  const clusters: TimelineSpan[][] = [];
  let current: TimelineSpan[] = [sorted[0]!];
  let clusterEnd = sorted[0]!.endTime.getTime();

  for (let i = 1; i < sorted.length; i++) {
    const span = sorted[i]!;
    if (span.startTime.getTime() < clusterEnd + OVERLAP_TOLERANCE_MS) {
      // Overlaps with current cluster
      current.push(span);
      clusterEnd = Math.max(clusterEnd, span.endTime.getTime());
    } else {
      // Gap found — finalize current cluster and start a new one
      clusters.push(current);
      current = [span];
      clusterEnd = span.endTime.getTime();
    }
  }
  clusters.push(current);

  return clusters;
}

function buildParentRow(node: TimelineSpan): SwimlaneRow {
  return {
    key: node.name.toLowerCase(),
    name: node.name,
    depth: 0,
    spans: [{ agent: node }],
    totalTokens: node.totalTokens,
    startTime: node.startTime,
    endTime: node.endTime,
  };
}

/**
 * Groups spans by name (case-insensitive), preserving the display name
 * from the first span encountered in each group.
 *
 * Returns entries in insertion order (first-seen order).
 */
function groupByName(spans: TimelineSpan[]): [string, TimelineSpan[]][] {
  const map = new Map<string, { displayName: string; spans: TimelineSpan[] }>();

  for (const span of spans) {
    const key = span.name.toLowerCase();
    const existing = map.get(key);
    if (existing) {
      existing.spans.push(span);
    } else {
      map.set(key, { displayName: span.name, spans: [span] });
    }
  }

  return Array.from(map.values()).map((g) => [g.displayName, g.spans]);
}

function buildRowFromGroup(
  displayName: string,
  spans: TimelineSpan[],
  depth = 1,
  parentKey = ""
): SwimlaneRow | null {
  // Sort spans by start time, end time as tiebreaker
  const sorted = [...spans].sort(compareByTime);

  const first = sorted[0];
  if (!first) {
    return null;
  }

  // Partition into overlapping clusters, then build RowSpans
  const rowSpans = partitionIntoClusters(sorted).map(
    (cluster): RowSpan =>
      cluster.length === 1 ? { agent: cluster[0]! } : { agents: cluster }
  );

  // Compute aggregated time range and tokens
  const startTime = first.startTime;
  const endTime = sorted.reduce(
    (latest, span) =>
      span.endTime.getTime() > latest.getTime() ? span.endTime : latest,
    first.endTime
  );
  const totalTokens = sorted.reduce((sum, span) => sum + span.totalTokens, 0);

  const key = parentKey
    ? `${parentKey}/${displayName.toLowerCase()}`
    : displayName.toLowerCase();

  return {
    key,
    name: displayName,
    depth,
    spans: rowSpans,
    totalTokens,
    startTime,
    endTime,
  };
}

// =============================================================================
// Flat (Fully Expanded) Computation
// =============================================================================

/**
 * Computes a fully expanded flat list of swimlane rows from the entire span tree.
 *
 * Unlike `computeSwimlaneRows` (which only shows direct children), this function
 * recursively walks all descendant spans in depth-first pre-order. Each row carries
 * a `depth` for indentation and a unique `key` for selection.
 *
 * Same-name non-overlapping spans (iterative) are collapsed onto a single row
 * with multiple bars. Same-name overlapping spans (parallel) are expanded into
 * separate numbered rows.
 */
export function computeFlatSwimlaneRows(
  root: TimelineSpan,
  options?: { includeUtility?: boolean }
): SwimlaneRow[] {
  const includeUtility = options?.includeUtility ?? false;
  const parentRow = buildParentRow(root);
  const childRows = flattenChildren(
    [root],
    0,
    root.name.toLowerCase(),
    includeUtility
  );
  return [parentRow, ...childRows];
}

/**
 * An entry produced by expanding a name group. Each entry becomes one row.
 * For iterative groups, there's a single entry with all spans merged.
 * For parallel groups, each span gets its own entry with a numbered name.
 */
interface FlatEntry {
  displayName: string;
  key: string;
  /** All TimelineSpans that contribute to this row's bars. */
  spans: TimelineSpan[];
  /** Pre-built RowSpans for this row (one SingleSpan per iterative span). */
  rowSpans: RowSpan[];
  totalTokens: number;
  startTime: Date;
  endTime: Date;
}

/**
 * Recursively flattens descendant spans into rows in depth-first pre-order.
 *
 * Accepts multiple parent nodes so that iterative spans at the same level
 * can have their children merged before recursing.
 *
 * For each name group, partitions into overlapping clusters:
 * - If no cluster has >1 span (all iterative/sequential) → one row, multiple bars
 * - If any cluster has >1 span (parallel) → separate numbered rows per span
 */
function flattenChildren(
  nodes: TimelineSpan[],
  parentDepth: number,
  parentKey: string,
  includeUtility: boolean
): SwimlaneRow[] {
  // Collect child spans, optionally filtering utility agents
  const children: TimelineSpan[] = [];
  for (const node of nodes) {
    for (const item of node.content) {
      if (item.type === "span" && (includeUtility || !item.utility)) {
        children.push(item);
      }
    }
  }
  if (children.length === 0) return [];

  const groups = groupByName(children);
  const depth = parentDepth + 1;

  // Expand each group into one or more FlatEntries
  const entries: FlatEntry[] = [];

  for (const [displayName, spans] of groups) {
    const sorted = [...spans].sort(compareByTime);
    const baseName = displayName.toLowerCase();
    const clusters = partitionIntoClusters(sorted);
    const hasParallel = clusters.some((c) => c.length > 1);

    if (!hasParallel) {
      // All non-overlapping (iterative): one row with one bar per cluster
      const rowSpans: RowSpan[] = sorted.map((s) => ({ agent: s }));
      const first = sorted[0]!;
      const endTime = sorted.reduce(
        (latest, s) =>
          s.endTime.getTime() > latest.getTime() ? s.endTime : latest,
        first.endTime
      );
      entries.push({
        displayName,
        key: `${parentKey}/${baseName}`,
        spans: sorted,
        rowSpans,
        totalTokens: sorted.reduce((sum, s) => sum + s.totalTokens, 0),
        startTime: first.startTime,
        endTime,
      });
    } else {
      // Has overlapping spans (parallel): separate numbered rows per span
      for (let i = 0; i < sorted.length; i++) {
        const span = sorted[i]!;
        entries.push({
          displayName: `${displayName} ${i + 1}`,
          key: `${parentKey}/${baseName}-${i + 1}`,
          spans: [span],
          rowSpans: [{ agent: span }],
          totalTokens: span.totalTokens,
          startTime: span.startTime,
          endTime: span.endTime,
        });
      }
    }
  }

  // Sort all entries by start time for correct visual order
  entries.sort((a, b) => compareByTime(a, b));

  // Emit rows with recursive descent
  const result: SwimlaneRow[] = [];
  for (const entry of entries) {
    result.push({
      key: entry.key,
      name: entry.displayName,
      depth,
      spans: entry.rowSpans,
      totalTokens: entry.totalTokens,
      startTime: entry.startTime,
      endTime: entry.endTime,
    });
    result.push(...flattenChildren(entry.spans, depth, entry.key, includeUtility));
  }

  return result;
}
