/**
 * Marker computation for the timeline UI.
 *
 * Collects error, compaction, and branch markers from a TimelineSpan's
 * content at configurable depth levels (direct, children, recursive).
 */

import type {
  TimelineEvent,
  TimelineSpan,
} from "../../components/transcript/timeline";
import type { Event } from "../../types/api-types";

// =============================================================================
// Types
// =============================================================================

export type MarkerKind = "error" | "compaction" | "branch";

export interface TimelineMarker {
  kind: MarkerKind;
  timestamp: Date;
  reference: string;
}

export type MarkerDepth = "direct" | "children" | "recursive";

// =============================================================================
// Event Classification
// =============================================================================

/**
 * Returns true if the event is an error event.
 *
 * An event is an error if:
 * - It's a ToolEvent with `.error !== null`
 * - It's a ModelEvent with `.error !== null` or `.output.error !== null`
 */
export function isErrorEvent(event: Event): boolean {
  if (event.event === "tool") {
    return event.error !== null;
  }
  if (event.event === "model") {
    return event.error !== null || event.output.error !== null;
  }
  return false;
}

/**
 * Returns true if the event is a compaction event.
 */
export function isCompactionEvent(event: Event): boolean {
  return event.event === "compaction";
}

// =============================================================================
// Main Function
// =============================================================================

/**
 * Collects timeline markers from a TimelineSpan at the specified depth.
 *
 * - `"direct"`: Only markers from the span's own TimelineEvent content.
 * - `"children"`: Own events + events from direct child spans.
 * - `"recursive"`: Full subtree traversal.
 *
 * Branch markers are always collected from the span's own branches
 * (not from child spans), regardless of depth.
 *
 * Results are sorted by timestamp.
 */
export function collectMarkers(
  node: TimelineSpan,
  depth: MarkerDepth
): TimelineMarker[] {
  const markers: TimelineMarker[] = [];

  // Collect event markers at the specified depth
  collectEventMarkers(node, depth, 0, markers);

  // Collect branch markers from this span's branches only
  collectBranchMarkers(node, markers);

  // Sort by timestamp
  markers.sort((a, b) => a.timestamp.getTime() - b.timestamp.getTime());

  return markers;
}

// =============================================================================
// Internal Helpers
// =============================================================================

/**
 * Collects error and compaction markers from event nodes.
 *
 * @param node The span to scan
 * @param depth The depth mode
 * @param currentLevel 0 = the root node itself, 1 = direct children, etc.
 * @param markers Accumulator array
 */
function collectEventMarkers(
  node: TimelineSpan,
  depth: MarkerDepth,
  currentLevel: number,
  markers: TimelineMarker[]
): void {
  for (const item of node.content) {
    if (item.type === "event") {
      addEventMarker(item, markers);
    } else if (item.type === "span" && shouldDescend(depth, currentLevel)) {
      collectEventMarkers(item, depth, currentLevel + 1, markers);
    }
  }
}

/**
 * Determines whether to descend into a child span based on depth mode.
 */
function shouldDescend(depth: MarkerDepth, currentLevel: number): boolean {
  if (depth === "direct") return false;
  if (depth === "children") return currentLevel === 0;
  // "recursive"
  return true;
}

/**
 * Adds a marker for a timeline event if it's an error or compaction event.
 */
function addEventMarker(
  eventNode: TimelineEvent,
  markers: TimelineMarker[]
): void {
  const event = eventNode.event;
  const uuid = event.uuid;

  if (isErrorEvent(event)) {
    markers.push({
      kind: "error",
      timestamp: eventNode.startTime,
      reference: uuid ?? "",
    });
  } else if (isCompactionEvent(event)) {
    markers.push({
      kind: "compaction",
      timestamp: eventNode.startTime,
      reference: uuid ?? "",
    });
  }
}

/**
 * Collects branch markers from a span's branches.
 *
 * Resolves the forkedAt UUID to a timestamp by searching the span's content.
 * Branches with unresolvable forkedAt are silently dropped.
 */
function collectBranchMarkers(
  node: TimelineSpan,
  markers: TimelineMarker[]
): void {
  for (const branch of node.branches) {
    const timestamp = resolveForkedAtTimestamp(node, branch.forkedAt);
    if (timestamp) {
      markers.push({
        kind: "branch",
        timestamp,
        reference: branch.forkedAt,
      });
    }
  }
}

/**
 * Resolves a forkedAt UUID to a timestamp by searching for the matching
 * event in the span's content.
 */
function resolveForkedAtTimestamp(
  node: TimelineSpan,
  forkedAt: string
): Date | null {
  if (!forkedAt) return null;

  for (const item of node.content) {
    if (item.type === "event" && item.event.uuid === forkedAt) {
      return item.startTime;
    }
  }
  return null;
}
