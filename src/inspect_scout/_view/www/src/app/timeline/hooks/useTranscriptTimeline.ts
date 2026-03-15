/**
 * Orchestration hook for timeline swimlanes in the transcript view.
 *
 * Bridges the flat Event[] from the transcript API to the timeline swimlane
 * pipeline: buildTimeline → useTimeline → layouts + selectedEvents.
 *
 * Always runs through collectRawEvents so that sourceSpans (used for
 * agent card rendering) are populated for the selected row.
 */

import { useMemo } from "react";

import {
  buildTimeline,
  convertServerTimeline,
  type Timeline,
  type TimelineSpan,
} from "../../../components/transcript/timeline";
import type { Event, ServerTimeline } from "../../../types/api-types";
import type { MinimapSelection } from "../components/TimelineMinimap";
import {
  collectRawEvents,
  computeMinimapSelection,
  getSelectedSpans,
  parseSelection,
} from "../timelineEventNodes";
import { type MarkerConfig, defaultMarkerConfig } from "../utils/markers";
import {
  computeRowLayouts,
  rowHasEvents,
  type RowLayout,
} from "../utils/swimlaneLayout";
import { isSingleSpan } from "../utils/swimlaneRows";
import { computeTimeMapping, type TimeMapping } from "../utils/timeMapping";

import { useActiveTimeline } from "./useActiveTimeline";
import {
  type TimelineOptions,
  type TimelineState,
  useTimeline,
} from "./useTimeline";

const emptySourceSpans: ReadonlyMap<string, TimelineSpan> = new Map();

interface TranscriptTimelineResult {
  /** The built Timeline. Always present (even for root-only timelines). */
  timeline: Timeline;
  /** Full useTimeline state (node, rows, navigation). */
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
  /** All available timelines (may be 1 or more). */
  timelines: Timeline[];
  /** Index of the currently active timeline. */
  activeTimelineIndex: number;
  /** Switch the active timeline by index. Resets selection. */
  setActiveTimeline: (index: number) => void;
  /** Map from row key → number of compaction regions (only for rows with compactions). */
  regionCounts: ReadonlyMap<string, number>;
}

export function useTranscriptTimeline(
  events: Event[],
  markerConfig: MarkerConfig = defaultMarkerConfig,
  timelineOptions?: TimelineOptions,
  serverTimelines?: ServerTimeline[]
): TranscriptTimelineResult {
  const includeUtility = timelineOptions?.includeUtility ?? false;
  const builtTimeline = useMemo(() => buildTimeline(events), [events]);
  const convertedTimelines = useMemo(
    () =>
      serverTimelines && serverTimelines.length > 0
        ? serverTimelines.map((tl) => convertServerTimeline(tl, events))
        : null,
    [serverTimelines, events]
  );
  const timelines = convertedTimelines ?? [builtTimeline];

  const {
    active: timeline,
    activeIndex: activeTimelineIndex,
    setActive: setActiveTimeline,
  } = useActiveTimeline(timelines);

  const state = useTimeline(timeline, timelineOptions);

  // Filter out child rows whose spans contain no events.
  // The parent row (depth 0) is always kept.
  const visibleRows = useMemo(
    () => state.rows.filter((row) => row.depth === 0 || rowHasEvents(row)),
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
    () =>
      computeRowLayouts(
        visibleRows,
        timeMapping,
        markerConfig.depth,
        markerConfig.kinds
      ),
    [visibleRows, timeMapping, markerConfig.depth, markerConfig.kinds]
  );

  const { selectedEvents, sourceSpans } = useMemo(() => {
    const parsed = parseSelection(state.selected);
    const spans = getSelectedSpans(state.rows, state.selected);
    if (spans.length === 0) {
      return { selectedEvents: events, sourceSpans: emptySourceSpans };
    }
    const collected = collectRawEvents(spans, {
      includeUtility,
      regionIndex: parsed?.regionIndex ?? null,
    });
    return {
      selectedEvents: collected.events,
      sourceSpans: collected.sourceSpans,
    };
  }, [events, state.rows, state.selected, includeUtility]);

  const minimapSelection = useMemo(
    () => computeMinimapSelection(state.rows, state.selected),
    [state.rows, state.selected]
  );

  // Compute region counts: for each single-span row, count compaction events + 1.
  // Only includes rows with at least one compaction event.
  const regionCounts = useMemo(() => {
    const counts = new Map<string, number>();
    for (const row of state.rows) {
      const firstSpan = row.spans[0];
      if (row.spans.length === 1 && firstSpan && isSingleSpan(firstSpan)) {
        const agent = firstSpan.agent;
        let compactionCount = 0;
        for (const item of agent.content) {
          if (item.type === "event" && item.event.event === "compaction") {
            compactionCount++;
          }
        }
        if (compactionCount > 0) {
          counts.set(row.key, compactionCount + 1);
        }
      }
    }
    return counts;
  }, [state.rows]);

  const hasTimeline =
    timeline.root.content.length > 0 &&
    timeline.root.content.some((item) => item.type === "span");

  return {
    timeline,
    state,
    layouts,
    timeMapping,
    rootTimeMapping,
    selectedEvents,
    sourceSpans,
    minimapSelection,
    hasTimeline,
    timelines,
    activeTimelineIndex,
    setActiveTimeline,
    regionCounts,
  };
}
