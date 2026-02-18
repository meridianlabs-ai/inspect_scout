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
  name: string;
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

/**
 * Returns true if two spans overlap in time, within the tolerance.
 * Two spans overlap if A starts before B ends and B starts before A ends.
 */
function spansOverlap(a: TimelineSpan, b: TimelineSpan): boolean {
  return (
    a.startTime.getTime() < b.endTime.getTime() + OVERLAP_TOLERANCE_MS &&
    b.startTime.getTime() < a.endTime.getTime() + OVERLAP_TOLERANCE_MS
  );
}

/**
 * Returns true if any pair of spans in the group overlap.
 */
function groupHasOverlap(spans: TimelineSpan[]): boolean {
  for (let i = 0; i < spans.length; i++) {
    for (let j = i + 1; j < spans.length; j++) {
      const a = spans[i];
      const b = spans[j];
      if (a && b && spansOverlap(a, b)) {
        return true;
      }
    }
  }
  return false;
}

// =============================================================================
// Main Computation
// =============================================================================

/**
 * Computes swimlane rows from a TimelineSpan's children.
 *
 * @returns Array of SwimlaneRow, with the parent row always first,
 *          followed by child rows ordered by earliest start time.
 */
export function computeSwimlaneRows(node: TimelineSpan): SwimlaneRow[] {
  // Parent row is always first
  const parentRow = buildParentRow(node);

  // Collect non-utility child spans
  const children = node.content.filter(
    (item): item is TimelineSpan => item.type === "span" && !item.utility
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

function buildParentRow(node: TimelineSpan): SwimlaneRow {
  return {
    name: node.name,
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
  spans: TimelineSpan[]
): SwimlaneRow | null {
  // Sort spans by start time, end time as tiebreaker
  const sorted = [...spans].sort(compareByTime);

  const first = sorted[0];
  if (!first) {
    return null;
  }

  // Determine row spans based on overlap
  let rowSpans: RowSpan[];
  if (sorted.length === 1) {
    rowSpans = [{ agent: first }];
  } else if (groupHasOverlap(sorted)) {
    // Any overlap → entire group is one ParallelSpan
    rowSpans = [{ agents: sorted }];
  } else {
    // No overlap → each span is a separate SingleSpan (iterative)
    rowSpans = sorted.map((span) => ({ agent: span }));
  }

  // Compute aggregated time range and tokens
  const startTime = first.startTime;
  const endTime = sorted.reduce(
    (latest, span) =>
      span.endTime.getTime() > latest.getTime() ? span.endTime : latest,
    first.endTime
  );
  const totalTokens = sorted.reduce((sum, span) => sum + span.totalTokens, 0);

  return {
    name: displayName,
    spans: rowSpans,
    totalTokens,
    startTime,
    endTime,
  };
}
