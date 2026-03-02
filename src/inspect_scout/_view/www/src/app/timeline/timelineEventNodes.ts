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
 * In the flat view, each row has exactly one SingleSpan, so this simply
 * returns the agent from the matching row.
 */
export function getSelectedSpans(
  rows: SwimlaneRow[],
  selected: string | null
): TimelineSpan[] {
  if (!selected) return [];

  const row = findRowByKey(rows, selected);
  if (!row) return [];

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
 * Returns the time range and token count for the selected row's span.
 */
export function computeMinimapSelection(
  rows: SwimlaneRow[],
  selected: string | null
): MinimapSelection | undefined {
  if (!selected) return undefined;
  const row = findRowByKey(rows, selected);
  if (!row) return undefined;

  // In the flat view, each row typically has a single span
  const allAgents = row.spans.flatMap(getAgents);
  if (allAgents.length === 0) return undefined;

  if (allAgents.length === 1) {
    const agent = allAgents[0]!;
    return {
      startTime: agent.startTime,
      endTime: agent.endTime,
      totalTokens: agent.totalTokens,
    };
  }

  // Multiple agents (shouldn't normally happen in flat view, but handle gracefully)
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
export function collectRawEvents(spans: TimelineSpan[]): CollectedEvents {
  const events: Event[] = [];
  const sourceSpans = new Map<string, TimelineSpan>();
  if (spans.length === 1) {
    // When viewing a single agent span, the spawning ToolEvent (which wraps
    // the entire agent execution) duplicates the first MODEL CALL's input and
    // the last ASSISTANT response. Detect and skip it at the top level only.
    const span = spans[0]!;
    const agentSpanId = span.spanType === "agent" ? span.id : undefined;
    collectFromContent(span.content, events, sourceSpans, agentSpanId);
  } else {
    // Multiple spans: wrap each in span_begin/span_end so the event tree
    // groups them, matching the drilled-in container behavior.
    collectFromContent(spans, events, sourceSpans);
  }
  return { events, sourceSpans };
}

function collectFromContent(
  content: ReadonlyArray<TimelineEvent | TimelineSpan>,
  out: Event[],
  sourceSpans: Map<string, TimelineSpan>,
  skipAgentSpanId?: string
): void {
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
      out.push(item.event);
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
      } else {
        // Non-agent spans: recurse into child content
        collectFromContent(item.content, out, sourceSpans);
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
 * Builds a lookup from span ID to the row key needed to select that span
 * in the swimlane UI.
 */
export function buildSpanSelectKeys(
  rows: SwimlaneRow[]
): ReadonlyMap<string, SpanSelectKey> {
  const keys = new Map<string, SpanSelectKey>();
  for (const row of rows) {
    for (const rowSpan of row.spans) {
      if (isSingleSpan(rowSpan)) {
        keys.set(rowSpan.agent.id, { key: row.key });
      } else {
        for (const agent of getAgents(rowSpan)) {
          keys.set(agent.id, { key: row.key });
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
