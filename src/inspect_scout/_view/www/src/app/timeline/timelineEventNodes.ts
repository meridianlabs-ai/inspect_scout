/**
 * Bridge from timeline spans to raw Event[] for the transcript display pipeline.
 *
 * Resolves the selected swimlane row to TimelineSpan(s), then walks their
 * content trees to produce a flat Event[] that can be fed through useEventNodes.
 * Child TimelineSpans are re-emitted as synthetic span_begin/span_end events
 * so treeifyEvents can reconstruct the hierarchy.
 */

import type {
  Event,
  SpanBeginEvent,
  SpanEndEvent,
} from "../../types/api-types";
import type {
  TimelineEvent,
  TimelineSpan,
} from "../../components/transcript/timeline";

import {
  type SwimLaneRow,
  isSingleSpan,
  isParallelSpan,
} from "./swimlaneRows";
import { parsePathSegment } from "./useTimeline";

/**
 * Resolves the selected swimlane row identifier to TimelineSpan(s).
 *
 * For single-span rows, returns the single agent. For parallel rows with a
 * span index suffix (e.g. "Explore-2"), returns the specific agent. For
 * parallel rows without a suffix, returns all agents.
 */
export function getSelectedSpans(
  rows: SwimLaneRow[],
  selected: string | null
): TimelineSpan[] {
  if (!selected) return [];

  const { name, spanIndex } = parsePathSegment(selected);
  const row = rows.find((r) => r.name.toLowerCase() === name.toLowerCase());
  if (!row) return [];

  const result: TimelineSpan[] = [];
  for (const rowSpan of row.spans) {
    if (isSingleSpan(rowSpan)) {
      result.push(rowSpan.agent);
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

/**
 * Collects raw Event[] from TimelineSpan content trees.
 *
 * Walks the content recursively. For TimelineEvent items, emits the wrapped
 * raw Event. For child TimelineSpan items, emits synthetic span_begin/span_end
 * events bracketing the recursed content, so treeifyEvents can rebuild the
 * parent-child hierarchy via span_id matching.
 */
export function collectRawEvents(spans: TimelineSpan[]): Event[] {
  const events: Event[] = [];
  for (const span of spans) {
    collectFromContent(span.content, events);
  }
  return events;
}

function collectFromContent(
  content: ReadonlyArray<TimelineEvent | TimelineSpan>,
  out: Event[]
): void {
  for (const item of content) {
    if (item.type === "event") {
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

      // Recurse into child content
      collectFromContent(item.content, out);

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
