/**
 * Bridge from timeline spans to raw Event[] for the transcript display pipeline.
 *
 * Resolves the selected swimlane row to TimelineSpan(s), then walks their
 * content trees to produce a flat Event[] that can be fed through useEventNodes.
 * Child TimelineSpans are re-emitted as synthetic span_begin/span_end events
 * so treeifyEvents can reconstruct the hierarchy.
 */

import type {
  TimelineEvent,
  TimelineSpan,
} from "../../components/transcript/timeline";
import { EventNode } from "../../components/transcript/types";
import type {
  Event,
  SpanBeginEvent,
  SpanEndEvent,
} from "../../types/api-types";

import type { MinimapSelection } from "./components/TimelineMinimap";
import { computeTimeEnvelope } from "./utils/swimlaneLayout";
import {
  type SwimlaneRow,
  getAgents,
  isSingleSpan,
} from "./utils/swimlaneRows";

// =============================================================================
// Selection parsing
// =============================================================================

/**
 * Parsed selection: a row key with an optional span index.
 *
 * Format: `"rowKey"` selects the whole row, `"rowKey:N"` selects
 * span index N (0-based) within an iterative row.
 */
export interface ParsedSelection {
  rowKey: string;
  spanIndex: number | null;
}

/**
 * Parses a selection string into row key + optional span index.
 * Returns null for null/empty input.
 */
export function parseSelection(
  selected: string | null
): ParsedSelection | null {
  if (!selected) return null;
  const colonIdx = selected.lastIndexOf(":");
  if (colonIdx === -1) return { rowKey: selected, spanIndex: null };
  const suffix = selected.slice(colonIdx + 1);
  const idx = Number(suffix);
  if (!Number.isInteger(idx) || idx < 0) {
    // Not a valid span index — treat the whole string as the row key
    return { rowKey: selected, spanIndex: null };
  }
  return { rowKey: selected.slice(0, colonIdx), spanIndex: idx };
}

/**
 * Builds a selection string from row key + optional span index.
 */
export function buildSelectionKey(rowKey: string, spanIndex?: number): string {
  if (spanIndex !== undefined) return `${rowKey}:${spanIndex}`;
  return rowKey;
}

// =============================================================================
// Row lookup
// =============================================================================

/** Find a swimlane row by key. */
function findRowByKey(
  rows: SwimlaneRow[],
  key: string
): SwimlaneRow | undefined {
  return rows.find((r) => r.key === key);
}

// =============================================================================
// Selected spans
// =============================================================================

/**
 * Resolves the selected swimlane row key to TimelineSpan(s).
 *
 * When the selection includes a span index (e.g. `"explore:1"`), returns
 * only that specific span. Otherwise returns all spans from the row.
 */
export function getSelectedSpans(
  rows: SwimlaneRow[],
  selected: string | null
): TimelineSpan[] {
  const parsed = parseSelection(selected);
  if (!parsed) return [];

  const row = findRowByKey(rows, parsed.rowKey);
  if (!row) return [];

  // Sub-selection: return only the indexed span
  if (parsed.spanIndex !== null) {
    const span = row.spans[parsed.spanIndex];
    if (!span) return [];
    return isSingleSpan(span) ? [span.agent] : getAgents(span);
  }

  // Whole row: return all spans
  const result: TimelineSpan[] = [];
  for (const rowSpan of row.spans) {
    if (isSingleSpan(rowSpan)) {
      result.push(rowSpan.agent);
    } else {
      result.push(...getAgents(rowSpan));
    }
  }
  return result;
}

// =============================================================================
// Minimap selection
// =============================================================================

/**
 * Computes the minimap selection for the currently selected swimlane row.
 *
 * When a span index is present, shows just that span's range.
 * Otherwise shows the full row's range.
 */
export function computeMinimapSelection(
  rows: SwimlaneRow[],
  selected: string | null
): MinimapSelection | undefined {
  const parsed = parseSelection(selected);
  if (!parsed) return undefined;
  const row = findRowByKey(rows, parsed.rowKey);
  if (!row) return undefined;

  // Determine which spans to include
  const spans =
    parsed.spanIndex !== null
      ? row.spans[parsed.spanIndex]
        ? [row.spans[parsed.spanIndex]!]
        : []
      : row.spans;

  const allAgents = spans.flatMap(getAgents);
  if (allAgents.length === 0) return undefined;

  if (allAgents.length === 1) {
    const agent = allAgents[0]!;
    return {
      startTime: agent.startTime,
      endTime: agent.endTime,
      totalTokens: agent.totalTokens,
    };
  }

  const envelope = computeTimeEnvelope(allAgents);
  const tokens = allAgents.reduce((sum, a) => sum + a.totalTokens, 0);
  return { ...envelope, totalTokens: tokens };
}

// =============================================================================
// Collected events
// =============================================================================

export interface CollectedEvents {
  events: Event[];
  /** Agent spans keyed by span ID, for attaching to EventNodes after tree construction. */
  sourceSpans: Map<string, TimelineSpan>;
}

/**
 * Collects raw Event[] from TimelineSpan content trees.
 *
 * When a single span is provided, walks its content directly (the span itself
 * is the implicit context). When multiple spans are provided, each is wrapped
 * in synthetic span_begin/span_end events so treeifyEvents can reconstruct
 * the grouping (e.g. parallel agents shown as collapsible sections).
 *
 * Agent spans (spanType === "agent") are emitted as empty span_begin/span_end
 * pairs with no child events — their content is accessed by selecting the
 * swimlane row. The returned sourceSpans map allows attaching the original
 * TimelineSpan to the resulting EventNodes for rich rendering.
 */
export function collectRawEvents(
  spans: TimelineSpan[],
  options?: { includeUtility?: boolean }
): CollectedEvents {
  const includeUtility = options?.includeUtility ?? false;
  const events: Event[] = [];
  const sourceSpans = new Map<string, TimelineSpan>();
  if (spans.length === 1) {
    // When viewing a single agent span, the spawning ToolEvent (which wraps
    // the entire agent execution) duplicates the first MODEL CALL's input and
    // the last ASSISTANT response. Detect and skip it at the top level only.
    const span = spans[0]!;
    const agentSpanId = span.spanType === "agent" ? span.id : undefined;
    collectFromContent(
      span.content,
      events,
      sourceSpans,
      agentSpanId,
      includeUtility
    );
  } else {
    // Multiple spans: wrap each in span_begin/span_end so the event tree
    // groups them, matching the drilled-in container behavior.
    collectFromContent(spans, events, sourceSpans, undefined, includeUtility);
  }
  return { events, sourceSpans };
}

function collectFromContent(
  content: ReadonlyArray<TimelineEvent | TimelineSpan>,
  out: Event[],
  sourceSpans: Map<string, TimelineSpan>,
  skipAgentSpanId?: string,
  includeUtility: boolean = false
): void {
  // Track agent tool_call_ids whose results are shown on the AgentCard,
  // so we can filter them from the next model event's input.
  const pendingToolCallIds = new Set<string>();

  for (const item of content) {
    if (item.type === "event") {
      // Skip the spawning ToolEvent when viewing a sub-agent's own content.
      // Match the specific agent_span_id so we only skip the tool that
      // spawned this exact agent, not any other agent-spawning tool.
      if (
        skipAgentSpanId &&
        item.event.event === "tool" &&
        item.event.agent_span_id === skipAgentSpanId
      ) {
        continue;
      }

      // Filter agent tool results from model event inputs — these are
      // already shown on the AgentCard, so don't duplicate them inline.
      if (item.event.event === "model" && pendingToolCallIds.size > 0) {
        const modelEvent = item.event;
        if (modelEvent.input && Array.isArray(modelEvent.input)) {
          const filteredInput = (
            modelEvent.input as Array<Record<string, unknown>>
          ).filter(
            (msg) =>
              !(
                msg.role === "tool" &&
                typeof msg.tool_call_id === "string" &&
                pendingToolCallIds.has(msg.tool_call_id)
              )
          );
          if (filteredInput.length !== modelEvent.input.length) {
            // Mark the event so ModelEventView knows agent tool results were
            // filtered and it should not crawl backward through input messages.
            const patched = {
              ...modelEvent,
              input: filteredInput,
              agentResultsFiltered: true,
            } as unknown as Event;
            out.push(patched);
            pendingToolCallIds.clear();
            continue;
          }
        }
      }

      out.push(item.event);
    } else if (!includeUtility && item.utility) {
      // Skip utility spans — internal model calls (e.g. file path extraction)
      // that should not appear in the event tree or outline.
      continue;
    } else {
      // Emit synthetic span_begin
      const beginEvent: SpanBeginEvent = {
        event: "span_begin",
        name: item.name,
        id: item.id,
        span_id: item.id,
        type: item.spanType,
        timestamp: item.startTime.toISOString(),
        parent_id: null,
        pending: false,
        working_start: 0,
        uuid: null,
        metadata: null,
      };
      out.push(beginEvent);

      if (item.spanType === "agent") {
        // Agent spans: emit empty begin/end pair. Content is accessed
        // by selecting the swimlane row, not by expanding in-place.
        sourceSpans.set(item.id, item);
        // Track agent tool_call_ids with results for filtering from next model event
        if (item.agentResult && item.id.startsWith("agent-")) {
          pendingToolCallIds.add(item.id.slice(6));
        }
      } else {
        // Non-agent spans: recurse into child content
        collectFromContent(
          item.content,
          out,
          sourceSpans,
          undefined,
          includeUtility
        );
      }

      // Emit synthetic span_end
      const endEvent: SpanEndEvent = {
        event: "span_end",
        id: `${item.id}-end`,
        span_id: item.id,
        timestamp: item.endTime.toISOString(),
        pending: false,
        working_start: 0,
        uuid: null,
        metadata: null,
      };
      out.push(endEvent);
    }
  }
}

// =============================================================================
// Span select key lookup
// =============================================================================

export interface SpanSelectKey {
  /** The row key to select. */
  key: string;
}

/**
 * Builds a lookup from span ID to the selection key needed to select that span
 * in the swimlane UI.
 *
 * For rows with multiple spans (iterative), each span ID maps to a key with
 * the span index suffix (e.g. `"explore:0"`). For single-span rows, the key
 * is just the row key.
 */
export function buildSpanSelectKeys(
  rows: SwimlaneRow[]
): ReadonlyMap<string, SpanSelectKey> {
  const keys = new Map<string, SpanSelectKey>();
  for (const row of rows) {
    const hasMultipleSpans = row.spans.length > 1;
    for (let i = 0; i < row.spans.length; i++) {
      const rowSpan = row.spans[i]!;
      const selectKey = hasMultipleSpans
        ? buildSelectionKey(row.key, i)
        : row.key;
      if (isSingleSpan(rowSpan)) {
        keys.set(rowSpan.agent.id, { key: selectKey });
      } else {
        for (const agent of getAgents(rowSpan)) {
          keys.set(agent.id, { key: selectKey });
        }
      }
    }
  }
  return keys;
}

// =============================================================================
// Source span attachment
// =============================================================================

/**
 * Walks the EventNode tree and attaches sourceSpan to any span_begin node
 * whose span_id matches an entry in the map. This links synthetic span events
 * back to their original TimelineSpan for rich rendering.
 */
export function attachSourceSpans(
  nodes: EventNode[],
  spanMap: ReadonlyMap<string, TimelineSpan>
): void {
  for (const node of nodes) {
    if (node.event.event === "span_begin") {
      const spanId = node.event.span_id;
      if (spanId) {
        const span = spanMap.get(spanId);
        if (span) node.sourceSpan = span;
      }
    }
    if (node.children.length > 0) {
      attachSourceSpans(node.children, spanMap);
    }
  }
}
