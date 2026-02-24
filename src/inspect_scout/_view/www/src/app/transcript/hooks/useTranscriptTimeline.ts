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
  type RowLayout,
} from "../../timeline/utils/swimlaneLayout";

interface TranscriptTimelineResult {
  /** The built Timeline, or null if events are empty. */
  timeline: Timeline | null;
  /** Full useTimeline state (node, rows, breadcrumbs, navigation). */
  state: TimelineState;
  /** Computed row layouts for the swimlane UI. */
  layouts: RowLayout[];
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

  const layouts = useMemo(
    () =>
      computeRowLayouts(
        state.rows,
        state.node.startTime,
        state.node.endTime,
        "direct"
      ),
    [state.rows, state.node.startTime, state.node.endTime]
  );

  const parentRowName = state.rows[0]?.name;
  const parentSelected = isParentSelected(state.selected, parentRowName);

  const selectedEvents = useMemo(() => {
    // Optimization: when parent/root is selected, use original events directly
    if (parentSelected) return events;

    const spans = getSelectedSpans(state.rows, state.selected);
    return collectRawEvents(spans);
  }, [events, parentSelected, state.rows, state.selected]);

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
    selectedEvents,
    minimapSelection,
    hasTimeline,
  };
}
