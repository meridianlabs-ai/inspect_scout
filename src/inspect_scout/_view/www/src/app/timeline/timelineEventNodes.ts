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
  ToolEvent,
} from "../../types/api-types";

import type { MinimapSelection } from "./components/TimelineMinimap";
import { parsePathSegment } from "./hooks/useTimeline";
import { computeTimeEnvelope } from "./utils/swimlaneLayout";
import {
  type SwimlaneRow,
  getAgents,
  isParallelSpan,
  isSingleSpan,
} from "./utils/swimlaneRows";

// =============================================================================
// Row lookup
// =============================================================================

/** Find a swimlane row by name (case-insensitive). */
function findRowByName(
  rows: SwimlaneRow[],
  name: string
): SwimlaneRow | undefined {
  return rows.find((r) => r.name.toLowerCase() === name.toLowerCase());
}

// =============================================================================
// Selected spans
// =============================================================================

/**
 * Resolves the selected swimlane row identifier to TimelineSpan(s).
 *
 * For single-span rows, returns the single agent. For parallel rows with a
 * span index suffix (e.g. "Explore-2"), returns the specific agent. For
 * parallel rows without a suffix, returns all agents.
 */
export function getSelectedSpans(
  rows: SwimlaneRow[],
  selected: string | null
): TimelineSpan[] {
  if (!selected) return [];

  const { name, spanIndex } = parsePathSegment(selected);
  const row = findRowByName(rows, name);
  if (!row) return [];

  const result: TimelineSpan[] = [];
  const targetIndex = spanIndex !== null ? spanIndex - 1 : null; // 0-based

  for (let i = 0; i < row.spans.length; i++) {
    const rowSpan = row.spans[i]!;
    if (isSingleSpan(rowSpan)) {
      // For iterative rows, only include the targeted SingleSpan
      if (targetIndex === null || i === targetIndex) {
        result.push(rowSpan.agent);
      }
    } else if (isParallelSpan(rowSpan)) {
      if (spanIndex !== null) {
        const agent = rowSpan.agents[spanIndex - 1];
        if (agent) result.push(agent);
      } else {
        result.push(...rowSpan.agents);
      }
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
 * Resolves a single visually-highlighted span: for iterative rows, the
 * specific SingleSpan is selected; for parallel rows with a span index,
 * the specific agent. Without an index, the envelope of all parallel agents
 * is returned.
 */
export function computeMinimapSelection(
  rows: SwimlaneRow[],
  selected: string | null
): MinimapSelection | undefined {
  if (!selected) return undefined;
  const { name, spanIndex } = parsePathSegment(selected);
  const row = findRowByName(rows, name);
  if (!row) return undefined;

  const targetIndex = (spanIndex ?? 1) - 1;
  for (const rowSpan of row.spans) {
    if (isSingleSpan(rowSpan)) {
      const singleIndex = row.spans.indexOf(rowSpan);
      if (singleIndex === targetIndex || row.spans.length === 1) {
        const agent = rowSpan.agent;
        return {
          startTime: agent.startTime,
          endTime: agent.endTime,
          totalTokens: agent.totalTokens,
        };
      }
    } else if (isParallelSpan(rowSpan)) {
      if (spanIndex !== null) {
        const agent = rowSpan.agents[spanIndex - 1];
        if (agent) {
          return {
            startTime: agent.startTime,
            endTime: agent.endTime,
            totalTokens: agent.totalTokens,
          };
        }
      }
      // No index → envelope of all parallel agents
      const agents = getAgents(rowSpan);
      const envelope = computeTimeEnvelope(agents);
      const tokens = agents.reduce((sum, a) => sum + a.totalTokens, 0);
      return { ...envelope, totalTokens: tokens };
    }
  }
  return undefined;
}

// =============================================================================
// Collected events
// =============================================================================

export interface CollectedEvents {
  events: Event[];
  /** Agent spans keyed by span ID, for attaching to EventNodes after tree construction. */
  sourceSpans: Map<string, TimelineSpan>;
  /** ToolEvents that precede agent spans, keyed by span ID. */
  agentToolEvents: Map<string, ToolEvent>;
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
  const agentToolEvents = new Map<string, ToolEvent>();
  if (spans.length === 1) {
    collectFromContent(spans[0]!.content, events, sourceSpans, agentToolEvents);
  } else {
    // Multiple spans: wrap each in span_begin/span_end so the event tree
    // groups them, matching the drilled-in container behavior.
    collectFromContent(spans, events, sourceSpans, agentToolEvents);
  }
  return { events, sourceSpans, agentToolEvents };
}

function collectFromContent(
  content: ReadonlyArray<TimelineEvent | TimelineSpan>,
  out: Event[],
  sourceSpans: Map<string, TimelineSpan>,
  agentToolEvents: Map<string, ToolEvent>
): void {
  for (let i = 0; i < content.length; i++) {
    const item = content[i]!;
    if (item.type === "event") {
      // Look-ahead: if this is a ToolEvent immediately followed by a matching
      // agent span, suppress the ToolEvent and store it for the AgentCardView
      // to display. Match via agent_span_id on the ToolEvent, falling back to
      // the legacy "agent-{toolEvent.id}" convention.
      if (item.event.event === "tool") {
        const next = content[i + 1];
        if (next && next.type === "span" && next.spanType === "agent") {
          const toolEvent = item.event;
          if (
            (toolEvent.agent_span_id != null &&
              toolEvent.agent_span_id === next.id) ||
            next.id === `agent-${toolEvent.id}`
          ) {
            agentToolEvents.set(next.id, toolEvent);
            continue; // skip emitting; the next iteration handles the span
          }
        }
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
        collectFromContent(item.content, out, sourceSpans, agentToolEvents);
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
  name: string;
  spanIndex?: number;
  /** True when the span is part of a parallel group (requires drill-down). */
  parallel?: boolean;
}

/**
 * Builds a lookup from span ID to the (name, spanIndex) pair needed to
 * select that span in the swimlane UI.
 *
 * For single-span rows, only the name is needed. For rows with multiple
 * spans (iterative or parallel), a 1-based spanIndex distinguishes them.
 * Parallel spans are flagged so the caller can drill down before selecting.
 */
export function buildSpanSelectKeys(
  rows: SwimlaneRow[]
): ReadonlyMap<string, SpanSelectKey> {
  const keys = new Map<string, SpanSelectKey>();
  for (const row of rows) {
    const needsIndex = row.spans.length > 1;
    for (let i = 0; i < row.spans.length; i++) {
      const rowSpan = row.spans[i]!;
      if (isSingleSpan(rowSpan)) {
        keys.set(rowSpan.agent.id, {
          name: row.name,
          spanIndex: needsIndex ? i + 1 : undefined,
        });
      } else if (isParallelSpan(rowSpan)) {
        for (let j = 0; j < rowSpan.agents.length; j++) {
          keys.set(rowSpan.agents[j]!.id, {
            name: row.name,
            spanIndex: j + 1,
            parallel: true,
          });
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
  spanMap: ReadonlyMap<string, TimelineSpan>,
  agentToolEvents?: ReadonlyMap<string, ToolEvent>
): void {
  for (const node of nodes) {
    if (node.event.event === "span_begin") {
      const spanId = node.event.span_id;
      if (spanId) {
        const span = spanMap.get(spanId);
        if (span) node.sourceSpan = span;
        const toolEvent = agentToolEvents?.get(spanId);
        if (toolEvent) node.agentToolEvent = toolEvent;
      }
    }
    if (node.children.length > 0) {
      attachSourceSpans(node.children, spanMap, agentToolEvents);
    }
  }
}
