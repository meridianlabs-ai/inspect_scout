/**
 * Orchestration hook for timeline swimlanes in the transcript view.
 *
 * Bridges the flat Event[] from the transcript API to the timeline swimlane
 * pipeline: buildTimeline → useTimeline → layouts + selectedEvents.
 *
 * When no child row is selected, returns the original events directly to
 * avoid the collectRawEvents round-trip.
 */

import { useEffect, useMemo, useRef } from "react";

import {
  buildTimeline,
  type Timeline,
} from "../../../components/transcript/timeline";
import type { Event } from "../../../types/api-types";
import type { MinimapSelection } from "../../timeline/components/TimelineMinimap";
import {
  type TimelineState,
  useTimeline,
} from "../../timeline/hooks/useTimeline";
import {
  collectRawEvents,
  computeMinimapSelection,
  getSelectedSpans,
} from "../../timeline/timelineEventNodes";
import {
  computeRowLayouts,
  rowHasEvents,
  type RowLayout,
} from "../../timeline/utils/swimlaneLayout";
import { computeTimeMapping, type TimeMapping } from "../../timeline/utils/timeMapping";

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
  /** Minimap selection for the breadcrumb row. */
  minimapSelection: MinimapSelection | undefined;
  /** Whether the timeline has meaningful structure (non-empty root with children). */
  hasTimeline: boolean;
}

/**
 * Determines whether the current selection is the parent/root row
 * (meaning all events should be shown without filtering).
 */
function isParentSelected(
  selected: string | null,
  parentRowName: string | undefined
): boolean {
  if (selected === null || parentRowName === undefined) return true;
  return selected.toLowerCase() === parentRowName.toLowerCase();
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

  const parentRowName = state.rows[0]?.name;
  const parentSelected = isParentSelected(state.selected, parentRowName);
  const atRoot = state.breadcrumbs.length <= 1;

  const selectedEvents = useMemo(() => {
    // Optimization: when the parent row is selected *at the root level*,
    // use original events directly to avoid the collectRawEvents round-trip.
    // When drilled down, the parent row represents a sub-span, so we must
    // still filter through getSelectedSpans → collectRawEvents.
    if (atRoot && parentSelected) return events;

    const spans = getSelectedSpans(state.rows, state.selected);
    return collectRawEvents(spans);
  }, [events, atRoot, parentSelected, state.rows, state.selected]);

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
    minimapSelection,
    hasTimeline,
  };
}
