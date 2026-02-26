/**
 * Piecewise-linear time mapping for gap compression.
 *
 * When a timeline has large idle gaps (> 5 min), this module compresses them
 * into small fixed-width regions so active periods get proportionally more
 * horizontal space. Uses the same 5-min threshold as computeIdleTime.
 */

import type {
  TimelineEvent,
  TimelineSpan,
} from "../../../components/transcript/timeline";

// =============================================================================
// Types
// =============================================================================

/** A detected gap region that gets compressed in the mapping. */
export interface GapRegion {
  /** Gap start in epoch ms. */
  startMs: number;
  /** Gap end in epoch ms. */
  endMs: number;
  /** Gap duration in ms. */
  durationMs: number;
  /** Compressed position range start in the mapping (0-100). */
  percentStart: number;
  /** Compressed position range end in the mapping (0-100). */
  percentEnd: number;
}

/** A time-to-percent mapping that may compress idle gaps. */
export interface TimeMapping {
  /** Convert a timestamp to a percentage position (0-100). */
  toPercent(timestamp: Date): number;
  /** Whether this mapping has any compressed gaps. */
  hasCompression: boolean;
  /** The detected gap regions (empty if no compression). */
  gaps: GapRegion[];
}

// =============================================================================
// Constants
// =============================================================================

/** Same threshold as computeIdleTime in timeline.ts — 5 minutes. */
const GAP_THRESHOLD_MS = 300_000;

/** Each compressed gap gets zero width — gaps simply vanish from the timeline. */
const GAP_PERCENT = 0;

/** Maximum total percentage allocated to all gaps combined. */
const MAX_TOTAL_GAP_PERCENT = 0;

// =============================================================================
// Internal Types
// =============================================================================

/** An active time interval (merged from content items). */
interface ActiveInterval {
  startMs: number;
  endMs: number;
}

/**
 * A segment in the piecewise mapping. Each segment maps a time range
 * to a percent range, either as an active region (proportional) or a
 * compressed gap (fixed small width).
 */
interface MappingSegment {
  startMs: number;
  endMs: number;
  percentStart: number;
  percentEnd: number;
}

// =============================================================================
// Public API
// =============================================================================

/**
 * Creates an identity (linear) time mapping with no compression.
 * Useful as a fallback or for timelines without idle gaps.
 */
export function createIdentityMapping(
  viewStart: Date,
  viewEnd: Date
): TimeMapping {
  const startMs = viewStart.getTime();
  const endMs = viewEnd.getTime();
  const range = endMs - startMs;

  return {
    toPercent(timestamp: Date): number {
      if (range <= 0) return 0;
      const offset = timestamp.getTime() - startMs;
      return Math.max(0, Math.min(100, (offset / range) * 100));
    },
    hasCompression: false,
    gaps: [],
  };
}

/**
 * Computes a TimeMapping for a timeline node.
 *
 * If the node has no idle time (idleTime === 0), returns an identity mapping
 * with zero overhead. Otherwise, detects gaps between content items and
 * compresses them into small fixed-width regions.
 */
export function computeTimeMapping(node: TimelineSpan): TimeMapping {
  // Fast exit: no idle time means no gaps to compress
  if (node.idleTime === 0) {
    return createIdentityMapping(node.startTime, node.endTime);
  }

  const nodeStartMs = node.startTime.getTime();
  const nodeEndMs = node.endTime.getTime();
  const nodeRange = nodeEndMs - nodeStartMs;
  if (nodeRange <= 0) {
    return createIdentityMapping(node.startTime, node.endTime);
  }

  // Extract time intervals from content items
  const intervals = extractIntervals(node.content);
  if (intervals.length === 0) {
    return createIdentityMapping(node.startTime, node.endTime);
  }

  // Merge overlapping intervals into active regions
  const activeRegions = mergeIntervals(intervals);

  // Find compressible gaps between active regions and node boundaries
  const rawGaps = findGaps(nodeStartMs, nodeEndMs, activeRegions);
  if (rawGaps.length === 0) {
    return createIdentityMapping(node.startTime, node.endTime);
  }

  // Allocate percentages: gaps get fixed small widths, active regions share the rest
  const totalActiveMs = activeRegions.reduce(
    (sum, r) => sum + (r.endMs - r.startMs),
    0
  );

  // Cap total gap percentage
  let gapPercentEach = GAP_PERCENT;
  const totalGapPercent = rawGaps.length * gapPercentEach;
  if (totalGapPercent > MAX_TOTAL_GAP_PERCENT) {
    gapPercentEach = MAX_TOTAL_GAP_PERCENT / rawGaps.length;
  }
  const actualTotalGapPercent = rawGaps.length * gapPercentEach;
  const activePercent = 100 - actualTotalGapPercent;

  // Build the segment list: interleave active regions and gaps
  const segments: MappingSegment[] = [];
  const gapRegions: GapRegion[] = [];
  let currentPercent = 0;

  // Walk through the timeline from start to end, alternating between
  // active regions and gaps. The gaps array is aligned with the spaces
  // between active regions (and boundaries).
  let gapIdx = 0;

  // Leading gap (nodeStart → first active region)
  if (rawGaps.length > 0 && rawGaps[0]!.startMs === nodeStartMs) {
    const gap = rawGaps[0]!;
    const percentEnd = currentPercent + gapPercentEach;
    segments.push({
      startMs: gap.startMs,
      endMs: gap.endMs,
      percentStart: currentPercent,
      percentEnd,
    });
    gapRegions.push({
      startMs: gap.startMs,
      endMs: gap.endMs,
      durationMs: gap.endMs - gap.startMs,
      percentStart: currentPercent,
      percentEnd,
    });
    currentPercent = percentEnd;
    gapIdx = 1;
  }

  for (let i = 0; i < activeRegions.length; i++) {
    const region = activeRegions[i]!;
    const regionDurationMs = region.endMs - region.startMs;
    const regionPercent =
      totalActiveMs > 0
        ? (regionDurationMs / totalActiveMs) * activePercent
        : activePercent / activeRegions.length;
    const percentEnd = currentPercent + regionPercent;

    segments.push({
      startMs: region.startMs,
      endMs: region.endMs,
      percentStart: currentPercent,
      percentEnd,
    });
    currentPercent = percentEnd;

    // Gap after this active region (if any)
    if (gapIdx < rawGaps.length) {
      const gap = rawGaps[gapIdx]!;
      // Verify this gap follows the current active region
      if (gap.startMs >= region.endMs - 1) {
        const gapPercentEnd = currentPercent + gapPercentEach;
        segments.push({
          startMs: gap.startMs,
          endMs: gap.endMs,
          percentStart: currentPercent,
          percentEnd: gapPercentEnd,
        });
        gapRegions.push({
          startMs: gap.startMs,
          endMs: gap.endMs,
          durationMs: gap.endMs - gap.startMs,
          percentStart: currentPercent,
          percentEnd: gapPercentEnd,
        });
        currentPercent = gapPercentEnd;
        gapIdx++;
      }
    }
  }

  // Build the toPercent function using binary search over segments
  const frozenSegments = segments;

  return {
    toPercent(timestamp: Date): number {
      const ms = timestamp.getTime();

      // Clamp to boundaries
      if (ms <= nodeStartMs) return 0;
      if (ms >= nodeEndMs) return 100;

      // Binary search for the segment containing this timestamp
      const seg = findSegment(frozenSegments, ms);
      if (!seg) return 0;

      // Linear interpolation within the segment
      const segRange = seg.endMs - seg.startMs;
      if (segRange <= 0) return seg.percentStart;

      const t = (ms - seg.startMs) / segRange;
      return seg.percentStart + t * (seg.percentEnd - seg.percentStart);
    },
    hasCompression: true,
    gaps: gapRegions,
  };
}

/**
 * Compute active time (seconds) within [startMs, endMs] by subtracting
 * overlapping gap durations from the mapping.
 */
export function computeActiveTime(
  mapping: TimeMapping,
  startMs: number,
  endMs: number
): number {
  const wallClockMs = endMs - startMs;
  let gapMs = 0;
  for (const gap of mapping.gaps) {
    const overlapStart = Math.max(gap.startMs, startMs);
    const overlapEnd = Math.min(gap.endMs, endMs);
    if (overlapEnd > overlapStart) {
      gapMs += overlapEnd - overlapStart;
    }
  }
  return Math.max(0, (wallClockMs - gapMs) / 1000);
}

// =============================================================================
// Internal Helpers
// =============================================================================

/** Recursively extract [startMs, endMs] intervals from leaf content items. */
function extractIntervals(
  content: ReadonlyArray<TimelineEvent | TimelineSpan>
): ActiveInterval[] {
  const intervals: ActiveInterval[] = [];
  for (const item of content) {
    if (item.type === "event") {
      // Leaf event — use its time range directly
      intervals.push({
        startMs: item.startTime.getTime(),
        endMs: item.endTime.getTime(),
      });
    } else {
      // Span — recurse into children to find leaf intervals
      const childIntervals = extractIntervals(item.content);
      if (childIntervals.length > 0) {
        intervals.push(...childIntervals);
      } else {
        // Span has no leaf content — use the span's own time range
        intervals.push({
          startMs: item.startTime.getTime(),
          endMs: item.endTime.getTime(),
        });
      }
    }
  }
  return intervals;
}

/** Sort intervals by start time and merge overlapping ones. */
function mergeIntervals(intervals: ActiveInterval[]): ActiveInterval[] {
  if (intervals.length === 0) return [];

  const sorted = [...intervals].sort((a, b) => a.startMs - b.startMs);
  const merged: ActiveInterval[] = [{ ...sorted[0]! }];

  for (let i = 1; i < sorted.length; i++) {
    const current = sorted[i]!;
    const last = merged[merged.length - 1]!;

    if (current.startMs <= last.endMs) {
      // Overlapping or adjacent — extend
      last.endMs = Math.max(last.endMs, current.endMs);
    } else {
      merged.push({ ...current });
    }
  }

  return merged;
}

/** Find gaps between active regions that exceed the threshold. */
function findGaps(
  nodeStartMs: number,
  nodeEndMs: number,
  activeRegions: ActiveInterval[]
): ActiveInterval[] {
  const gaps: ActiveInterval[] = [];

  // Leading gap: node start → first active region
  if (activeRegions.length > 0) {
    const firstStart = activeRegions[0]!.startMs;
    if (firstStart - nodeStartMs > GAP_THRESHOLD_MS) {
      gaps.push({ startMs: nodeStartMs, endMs: firstStart });
    }
  }

  // Gaps between consecutive active regions
  for (let i = 1; i < activeRegions.length; i++) {
    const prevEnd = activeRegions[i - 1]!.endMs;
    const nextStart = activeRegions[i]!.startMs;
    if (nextStart - prevEnd > GAP_THRESHOLD_MS) {
      gaps.push({ startMs: prevEnd, endMs: nextStart });
    }
  }

  // Trailing gap: last active region → node end
  if (activeRegions.length > 0) {
    const lastEnd = activeRegions[activeRegions.length - 1]!.endMs;
    if (nodeEndMs - lastEnd > GAP_THRESHOLD_MS) {
      gaps.push({ startMs: lastEnd, endMs: nodeEndMs });
    }
  }

  return gaps;
}

/** Binary search for the segment containing a given timestamp. */
function findSegment(
  segments: MappingSegment[],
  ms: number
): MappingSegment | null {
  let lo = 0;
  let hi = segments.length - 1;

  while (lo <= hi) {
    const mid = (lo + hi) >>> 1;
    const seg = segments[mid]!;

    if (ms < seg.startMs) {
      hi = mid - 1;
    } else if (ms > seg.endMs) {
      lo = mid + 1;
    } else {
      return seg;
    }
  }

  // Timestamp falls between segments (shouldn't happen with correct gap detection,
  // but handle gracefully by returning the nearest segment)
  if (lo < segments.length) return segments[lo]!;
  if (hi >= 0) return segments[hi]!;
  return null;
}
