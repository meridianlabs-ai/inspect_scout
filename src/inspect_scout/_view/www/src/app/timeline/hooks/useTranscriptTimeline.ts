/**
 * Orchestration hook for timeline swimlanes in the transcript view.
 *
 * Bridges the flat Event[] from the transcript API to the timeline swimlane
 * pipeline: buildTimeline → useTimeline → layouts + selectedEvents.
 *
 * Always runs through collectRawEvents so that sourceSpans (used for
 * agent card rendering) are populated for the selected row.
 */

import { useEffect, useMemo, useRef } from "react";

import {
  buildTimeline,
  type Timeline,
  type TimelineSpan,
} from "../../../components/transcript/timeline";
import type { Event } from "../../../types/api-types";
import type { MinimapSelection } from "../components/TimelineMinimap";
import {
  collectRawEvents,
  computeMinimapSelection,
  getSelectedSpans,
} from "../timelineEventNodes";
import {
  computeRowLayouts,
  rowHasEvents,
  type RowLayout,
} from "../utils/swimlaneLayout";
import { computeTimeMapping, type TimeMapping } from "../utils/timeMapping";

import { type TimelineState, useTimeline } from "./useTimeline";

const emptySourceSpans: ReadonlyMap<string, TimelineSpan> = new Map();

interface TranscriptTimelineResult {
  /** The built Timeline, or null if events are empty. */
  timeline: Timeline | null;
  /** Full useTimeline state (node, rows, breadcrumbs, navigation). */
  state: TimelineState;
  /** Computed row layouts for the swimlane UI. */
  layouts: RowLayout[];
  /** Time mapping for the current node (may compress gaps). */
  timeMapping: TimeMapping;
  /** Time mapping for the root node (for minimap). */
  rootTimeMapping: TimeMapping;
  /** Events scoped to the selected swimlane row (or all events if no child selected). */
  selectedEvents: Event[];
  /** Agent spans keyed by span ID, for attaching to EventNodes. */
  sourceSpans: ReadonlyMap<string, TimelineSpan>;
  /** Minimap selection for the breadcrumb row. */
  minimapSelection: MinimapSelection | undefined;
  /** Whether the timeline has meaningful structure (non-empty root with children). */
  hasTimeline: boolean;
}

export function useTranscriptTimeline(
  events: Event[]
): TranscriptTimelineResult {
  const timeline = useMemo(() => buildTimeline(events), [events]);

  const state = useTimeline(timeline);

  // Reset drill-down path when the timeline changes (e.g. navigating transcripts)
  const prevTimelineRef = useRef(timeline);
  useEffect(() => {
    if (prevTimelineRef.current !== timeline) {
      prevTimelineRef.current = timeline;
      state.navigateTo("");
    }
    // Only react to timeline identity changes, not state.navigateTo
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [timeline]);

  // Filter out child rows whose spans contain no events.
  // The parent row (index 0) is always kept.
  const visibleRows = useMemo(
    () => state.rows.filter((row, i) => i === 0 || rowHasEvents(row)),
    [state.rows]
  );

  const timeMapping = useMemo(
    () => computeTimeMapping(state.node),
    [state.node]
  );

  const rootTimeMapping = useMemo(
    () => computeTimeMapping(timeline.root),
    [timeline.root]
  );

  const layouts = useMemo(
    () => computeRowLayouts(visibleRows, timeMapping, "direct"),
    [visibleRows, timeMapping]
  );

  const { selectedEvents, sourceSpans } = useMemo(() => {
    const spans = getSelectedSpans(state.rows, state.selected);
    if (spans.length === 0) {
      return { selectedEvents: events, sourceSpans: emptySourceSpans };
    }
    const collected = collectRawEvents(spans);
    return {
      selectedEvents: collected.events,
      sourceSpans: collected.sourceSpans,
    };
  }, [events, state.rows, state.selected]);

  const minimapSelection = useMemo(
    () => computeMinimapSelection(state.rows, state.selected),
    [state.rows, state.selected]
  );

  const hasTimeline =
    timeline.root.content.length > 0 &&
    timeline.root.content.some((item) => item.type === "span");

  return {
    timeline: hasTimeline ? timeline : null,
    state,
    layouts,
    timeMapping,
    rootTimeMapping,
    selectedEvents,
    sourceSpans,
    minimapSelection,
    hasTimeline,
  };
}
