/**
 * Swimlane layout computation for the timeline UI.
 *
 * Maps swimlane rows + a time range to percentage-based positions for CSS
 * rendering. All functions are pure with no DOM or React dependencies.
 */

import type {
  TimelineEvent,
  TimelineSpan,
} from "../../../components/transcript/timeline";
import { formatPrettyDecimal } from "../../../utils/format";

import { type MarkerDepth, type MarkerKind, collectMarkers } from "./markers";
import {
  type RowSpan,
  type SwimlaneRow,
  getAgents,
  isParallelSpan,
  isSingleSpan,
} from "./swimlaneRows";
import type { TimeMapping } from "./timeMapping";

// =============================================================================
// Types
// =============================================================================

/** Position of a single bar fill within the bar area, in percentages (0-100). */
export interface BarPosition {
  left: number;
  width: number;
}

/** Positioned span with bar position and metadata for rendering. */
export interface PositionedSpan {
  /** Bar position as percentage within the view range. */
  bar: BarPosition;
  /** Whether this span can be drilled into. */
  drillable: boolean;
  /** Number of child spans (for drill-down label). 0 if not drillable. */
  childCount: number;
  /** For ParallelSpan, the number of agents. Null for SingleSpan. */
  parallelCount: number | null;
  /** Task description for tooltip, if available. */
  description: string | null;
}

/** Positioned marker within the bar area. */
export interface PositionedMarker {
  /** Percentage offset from left edge (0-100). */
  left: number;
  /** The marker kind for rendering the correct glyph. */
  kind: MarkerKind;
  /** Reference identifier (forkedAt UUID for branches, event UUID for others). */
  reference: string;
  /** Human-readable detail for tooltip display. */
  tooltip: string;
}

/** Complete layout data for a single swimlane row. */
export interface RowLayout {
  /** Row name (for label column). */
  name: string;
  /** Whether this is the parent row (index 0). */
  isParent: boolean;
  /** Positioned spans (fills + chevrons). */
  spans: PositionedSpan[];
  /** Positioned markers. */
  markers: PositionedMarker[];
  /** Total tokens for the token column. */
  totalTokens: number;
  /** Parallel agent count for label display, or null if not parallel. */
  parallelCount: number | null;
}

// =============================================================================
// Percentage Computation
// =============================================================================

/**
 * Computes a single percentage position for a timestamp within a view range.
 * Result is clamped to [0, 100]. Returns 0 for zero-duration view ranges.
 */
export function timestampToPercent(
  timestamp: Date,
  viewStart: Date,
  viewEnd: Date
): number {
  const range = viewEnd.getTime() - viewStart.getTime();
  if (range <= 0) return 0;

  const offset = timestamp.getTime() - viewStart.getTime();
  return Math.max(0, Math.min(100, (offset / range) * 100));
}

/**
 * Computes the bar position (left + width) for a time range within a view range.
 * Both left and width are clamped so the bar stays within [0, 100].
 */
export function computeBarPosition(
  spanStart: Date,
  spanEnd: Date,
  viewStart: Date,
  viewEnd: Date
): BarPosition {
  const left = timestampToPercent(spanStart, viewStart, viewEnd);
  const right = timestampToPercent(spanEnd, viewStart, viewEnd);
  return { left, width: Math.max(0, right - left) };
}

// =============================================================================
// Drillability
// =============================================================================

/**
 * Determines whether a RowSpan is drillable.
 *
 * A SingleSpan is drillable if its agent has non-utility child spans.
 * A ParallelSpan is always drillable (drill reveals individual instances).
 */
export function isDrillable(span: RowSpan): boolean {
  if (isParallelSpan(span)) return true;

  if (isSingleSpan(span)) {
    return span.agent.content.some(
      (item): item is TimelineSpan => item.type === "span" && !item.utility
    );
  }

  return false;
}

/** Counts the drillable children for disclosure label text. */
function drillableChildCount(span: RowSpan): number {
  if (isParallelSpan(span)) return span.agents.length;
  if (isSingleSpan(span)) {
    return span.agent.content.filter(
      (item): item is TimelineSpan => item.type === "span" && !item.utility
    ).length;
  }
  return 0;
}

// =============================================================================
// Time Envelope
// =============================================================================

interface HasTimeRange {
  startTime: Date;
  endTime: Date;
}

/**
 * Computes the time envelope (earliest start, latest end) of a non-empty array.
 * Useful for computing the bounding range of parallel agents or branches.
 */
export function computeTimeEnvelope<T extends HasTimeRange>(
  items: T[]
): { startTime: Date; endTime: Date } {
  const first = items[0]!;
  let startTime = first.startTime;
  let endTime = first.endTime;
  for (let i = 1; i < items.length; i++) {
    const item = items[i]!;
    if (item.startTime < startTime) startTime = item.startTime;
    if (item.endTime > endTime) endTime = item.endTime;
  }
  return { startTime, endTime };
}

// =============================================================================
// Token Formatting
// =============================================================================

/**
 * Formats a token count for compact display: "48.5k", "1.2M", etc.
 * Uses rounding thresholds so values like 999,950 display as "1.0M" not "1000.0k".
 */
export function formatTokenCount(tokens: number): string {
  if (tokens >= 999_950) {
    return `${formatPrettyDecimal(tokens / 1_000_000, 1)}M`;
  }
  if (tokens >= 1_000) {
    return `${formatPrettyDecimal(tokens / 1_000, 1)}k`;
  }
  return String(tokens);
}

// =============================================================================
// Row Layout Computation
// =============================================================================

/**
 * Computes the full layout for all swimlane rows.
 *
 * The TimeMapping defines how timestamps map to percentage positions. When
 * gap compression is active, idle gaps are compressed into narrow regions.
 * Markers are collected at the specified depth for each row's spans.
 */
export function computeRowLayouts(
  rows: SwimlaneRow[],
  mapping: TimeMapping,
  markerDepth: MarkerDepth
): RowLayout[] {
  return rows.map((row, index) => {
    const isParent = index === 0;

    // Position each RowSpan
    const spans = row.spans.map((rowSpan): PositionedSpan => {
      if (isSingleSpan(rowSpan)) {
        const bar = computeBarFromMapping(
          rowSpan.agent.startTime,
          rowSpan.agent.endTime,
          mapping
        );
        const drillable = !isParent && isDrillable(rowSpan);
        return {
          bar,
          drillable,
          childCount: drillable ? drillableChildCount(rowSpan) : 0,
          parallelCount: null,
          description: rowSpan.agent.description ?? null,
        };
      }

      // ParallelSpan: envelope from earliest start to latest end
      const agents = rowSpan.agents;
      const envelope = computeTimeEnvelope(agents);
      const bar = computeBarFromMapping(
        envelope.startTime,
        envelope.endTime,
        mapping
      );
      return {
        bar,
        drillable: !isParent,
        childCount: !isParent ? agents.length : 0,
        parallelCount: agents.length,
        description: null,
      };
    });

    // Collect markers for this row
    const markers = collectRowMarkers(row, markerDepth, mapping);

    // Derive row-level parallel count from spans
    const rowParallelCount =
      spans.length === 1 && spans[0]!.parallelCount !== null
        ? spans[0]!.parallelCount
        : null;

    return {
      name: row.name,
      isParent,
      spans,
      markers,
      totalTokens: row.totalTokens,
      parallelCount: rowParallelCount,
    };
  });
}

// =============================================================================
// Mapping-based bar position
// =============================================================================

/** Computes bar position using a TimeMapping (which may compress gaps). */
function computeBarFromMapping(
  spanStart: Date,
  spanEnd: Date,
  mapping: TimeMapping
): BarPosition {
  const left = mapping.toPercent(spanStart);
  const right = mapping.toPercent(spanEnd);
  return { left, width: Math.max(0, right - left) };
}

// =============================================================================
// Internal Helpers
// =============================================================================

/** Returns true if a TimelineSpan has any TimelineEvent items in its content tree. */
export function spanHasEvents(span: TimelineSpan): boolean {
  for (const item of span.content) {
    if (item.type === "event") return true;
    if (item.type === "span" && spanHasEvents(item)) return true;
  }
  return false;
}

/** Returns true if any agent across all spans in a row has events. */
export function rowHasEvents(row: SwimlaneRow): boolean {
  return row.spans.some((rowSpan) => getAgents(rowSpan).some(spanHasEvents));
}

/**
 * Collects and positions markers for a single row.
 *
 * For the parent row, markers come from the parent span itself.
 * For child rows, markers are collected from each span's agent and merged.
 */
function collectRowMarkers(
  row: SwimlaneRow,
  depth: MarkerDepth,
  mapping: TimeMapping
): PositionedMarker[] {
  const allMarkers: PositionedMarker[] = [];

  for (const rowSpan of row.spans) {
    const agents = getAgents(rowSpan);

    for (const agent of agents) {
      const markers = collectMarkers(agent, depth);

      for (const m of markers) {
        allMarkers.push({
          left: mapping.toPercent(m.timestamp),
          kind: m.kind,
          reference: m.reference,
          tooltip: m.tooltip,
        });
      }
    }
  }

  // Sort by position
  allMarkers.sort((a, b) => a.left - b.left);
  return allMarkers;
}

// =============================================================================
// Debug
// =============================================================================

/** Pretty-print a RowSpan tree for debugging. Paste output to share context. */
export function debugRowSpan(span: RowSpan): string {
  const lines: string[] = [];
  const agents = getAgents(span);
  const kind = isSingleSpan(span) ? "Single" : `Parallel(${agents.length})`;
  lines.push(`[${kind}]`);
  for (const agent of agents) {
    printSpan(agent, 1, lines);
  }
  return lines.join("\n");
}

function printSpan(span: TimelineSpan, depth: number, lines: string[]): void {
  const indent = "  ".repeat(depth);
  const flags = [
    span.utility && "utility",
    span.spanType && `type=${span.spanType}`,
  ]
    .filter(Boolean)
    .join(", ");
  const flagStr = flags ? ` (${flags})` : "";
  const childSpans = span.content.filter(
    (c): c is TimelineSpan => c.type === "span"
  );
  const childEvents = span.content.filter(
    (c): c is TimelineEvent => c.type === "event"
  );
  const eventTypes = childEvents
    .map((e) => e.event.event)
    .reduce<Record<string, number>>((acc, t) => {
      acc[t] = (acc[t] ?? 0) + 1;
      return acc;
    }, {});
  const eventSummary = Object.entries(eventTypes)
    .map(([t, n]) => (n > 1 ? `${t}×${n}` : t))
    .join(", ");
  lines.push(
    `${indent}span "${span.name}" [${childEvents.length} events (${eventSummary}), ${childSpans.length} child spans, ${span.totalTokens} tokens]${flagStr}`
  );
  for (const child of childSpans) {
    printSpan(child, depth + 1, lines);
  }
}
