import clsx from "clsx";
import {
  CSSProperties,
  FC,
  RefObject,
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import { ApplicationIcons } from "../../../components/icons";
import { NoContentsPanel } from "../../../components/NoContentsPanel";
import { StickyScroll } from "../../../components/StickyScroll";
import { useEventNodes } from "../../../components/transcript/hooks/useEventNodes";
import { TranscriptOutline } from "../../../components/transcript/outline/TranscriptOutline";
import { TimelineSelectContext } from "../../../components/transcript/TimelineSelectContext";
import {
  TranscriptViewNodes,
  type TranscriptViewNodesHandle,
} from "../../../components/transcript/TranscriptViewNodes";
import {
  EventNode,
  kCollapsibleEventTypes,
  kTranscriptCollapseScope,
} from "../../../components/transcript/types";
import { useProperty } from "../../../state/hooks/useProperty";
import { useStore } from "../../../state/store";
import type { Event } from "../../../types/api-types";
import type { TimelineOptions } from "../hooks/useTimeline";
import { useTimelineConfig } from "../hooks/useTimelineConfig";
import { useTranscriptTimeline } from "../hooks/useTranscriptTimeline";
import { buildSpanSelectKeys } from "../timelineEventNodes";
import type { MarkerConfig } from "../utils/markers";

import styles from "./TimelineEventsView.module.css";
import { TimelineSwimLanes } from "./TimelineSwimLanes";

// =============================================================================
// Types
// =============================================================================

interface TimelineEventsViewProps {
  /** Raw events to display. Runs the full timeline pipeline internally. */
  events: Event[];
  /** Scroll container for StickyScroll and virtual list. */
  scrollRef: RefObject<HTMLDivElement | null>;
  /** Base offset for sticky positioning (e.g. tab bar height). Default: 0. */
  offsetTop?: number;
  /** Deep-link to a specific event on mount. */
  initialEventId?: string | null;
  /** Initial outline state when no persistent preference exists. Default: false (collapsed). */
  defaultOutlineExpanded?: boolean;
  /** Unique ID for the virtual list. */
  id: string;
  /** Bulk collapse/expand of all collapsible events. undefined = no-op. */
  collapsed?: boolean;
  /** Called when a marker (error, compaction) is clicked on the swimlane. */
  onMarkerNavigate?: (eventId: string) => void;
  /** Controls which marker kinds are shown and at what depth. */
  markerConfig?: MarkerConfig;
  /** Controls swimlane visibility. `"auto"` shows when data has child spans. Default: `"auto"`. */
  timeline?: true | false | "auto";
  /** Controls which agents are included in the timeline. */
  agentConfig?: TimelineOptions;
  className?: string;
}

// =============================================================================
// Helpers
// =============================================================================

const collectAllCollapsibleIds = (
  nodes: EventNode[]
): Record<string, boolean> => {
  const result: Record<string, boolean> = {};
  const traverse = (nodeList: EventNode[]) => {
    for (const node of nodeList) {
      if (kCollapsibleEventTypes.includes(node.event.event)) {
        result[node.id] = true;
      }
      if (node.children.length > 0) {
        traverse(node.children);
      }
    }
  };
  traverse(nodes);
  return result;
};

// =============================================================================
// Component
// =============================================================================

export const TimelineEventsView: FC<TimelineEventsViewProps> = ({
  events,
  scrollRef,
  offsetTop = 0,
  initialEventId,
  defaultOutlineExpanded = false,
  id,
  collapsed,
  onMarkerNavigate,
  markerConfig,
  timeline: timelineProp = "auto",
  agentConfig,
  className,
}) => {
  // ---------------------------------------------------------------------------
  // Timeline config (persistent user preferences)
  // ---------------------------------------------------------------------------

  const timelineConfig = useTimelineConfig();

  // Props override hook values when explicitly provided
  const resolvedMarkerConfig = markerConfig ?? timelineConfig.markerConfig;
  const resolvedAgentConfig = agentConfig ?? timelineConfig.agentConfig;

  // ---------------------------------------------------------------------------
  // Timeline pipeline
  // ---------------------------------------------------------------------------

  const {
    timeline: timelineData,
    state: timelineState,
    layouts: timelineLayouts,
    rootTimeMapping,
    selectedEvents,
    sourceSpans,
    minimapSelection,
    hasTimeline,
    timelines,
    activeTimelineIndex,
    setActiveTimeline,
  } = useTranscriptTimeline(events, resolvedMarkerConfig, resolvedAgentConfig);

  // ---------------------------------------------------------------------------
  // Span selection context (agent card clicks → swimlane selection)
  // ---------------------------------------------------------------------------

  const spanSelectKeys = useMemo(
    () => buildSpanSelectKeys(timelineState.rows),
    [timelineState.rows]
  );
  const { select: timelineSelect } = timelineState;
  const selectBySpanId = useCallback(
    (spanId: string) => {
      const key = spanSelectKeys.get(spanId);
      if (!key) return;
      timelineSelect(key.key);
    },
    [spanSelectKeys, timelineSelect]
  );

  // ---------------------------------------------------------------------------
  // Sticky swimlane state
  // ---------------------------------------------------------------------------

  const [isSwimLaneSticky, setIsSwimLaneSticky] = useState(false);
  const [stickySwimLaneHeight, setStickySwimLaneHeight] = useState(0);
  const swimLaneStickyContentRef = useRef<HTMLDivElement | null>(null);

  const handleSwimLaneStickyChange = useCallback((sticky: boolean) => {
    setIsSwimLaneSticky(sticky);
    if (!sticky) {
      setStickySwimLaneHeight(0);
    }
  }, []);

  // Measure the sticky swimlane height via ResizeObserver
  useEffect(() => {
    const el = swimLaneStickyContentRef.current;
    if (!isSwimLaneSticky || !el) {
      return;
    }
    const observer = new ResizeObserver(() => {
      setStickySwimLaneHeight(el.getBoundingClientRect().height);
    });
    observer.observe(el);
    setStickySwimLaneHeight(el.getBoundingClientRect().height);
    return () => observer.disconnect();
  }, [isSwimLaneSticky]);

  // ---------------------------------------------------------------------------
  // Event nodes
  // ---------------------------------------------------------------------------

  const { eventNodes, defaultCollapsedIds } = useEventNodes(
    selectedEvents,
    false,
    sourceSpans
  );
  const hasMatchingEvents = eventNodes.length > 0;

  // Ref to the event list for imperative scroll-to-event from outline clicks.
  const eventsListRef = useRef<TranscriptViewNodesHandle>(null);
  const handleOutlineNavigate = useCallback((eventId: string) => {
    eventsListRef.current?.scrollToEvent(eventId);
  }, []);

  // Per-agent scroll position persistence using Virtuoso StateSnapshot.
  // Each agent gets its own Virtuoso instance (via React `key`) so that
  // item measurements and scroll position are preserved independently.
  // On first visit to an agent, scroll to top since the shared scroll
  // container may still be at the previous agent's offset.
  const selected = timelineState.selected;
  const eventsListId = selected ? `${id}:${selected}` : id;
  const listPositions = useStore((state) => state.listPositions);
  const clearListPosition = useStore((state) => state.clearListPosition);

  // When the selection changes, scroll to top if the new agent has no
  // saved Virtuoso state (first visit). Returning visits are handled by
  // Virtuoso's restoreStateFrom on remount.
  useLayoutEffect(() => {
    if (initialEventId) return; // deep-link takes priority

    const virtuosoKey = `live-virtual-list-${eventsListId}`;
    if (!listPositions[virtuosoKey] && scrollRef.current) {
      scrollRef.current.scrollTo({ top: 0 });
    }
  }, [eventsListId, initialEventId, scrollRef, listPositions]);

  // Clean up per-agent state when the transcript panel unmounts
  // (e.g. navigating to a different transcript).
  const clearTranscriptOutlineId = useStore(
    (state) => state.clearTranscriptOutlineId
  );
  const listPositionsRef = useRef(listPositions);
  useEffect(() => {
    listPositionsRef.current = listPositions;
  }, [listPositions]);

  useEffect(() => {
    const prefix = `live-virtual-list-${id}:`;
    return () => {
      // Clear per-agent Virtuoso snapshots
      for (const key of Object.keys(listPositionsRef.current)) {
        if (key.startsWith(prefix)) {
          clearListPosition(key);
        }
      }
      // Clear stale outline highlight
      clearTranscriptOutlineId();
    };
  }, [id, clearListPosition, clearTranscriptOutlineId]);

  // Bulk collapse/expand effect driven by parent's `collapsed` prop
  const setCollapsedEvents = useStore(
    (state) => state.setTranscriptCollapsedEvents
  );
  useEffect(() => {
    if (events.length <= 0 || collapsed === undefined) {
      return;
    }
    if (!collapsed && Object.keys(defaultCollapsedIds).length > 0) {
      setCollapsedEvents(kTranscriptCollapseScope, defaultCollapsedIds);
    } else if (collapsed) {
      const allCollapsibleIds = collectAllCollapsibleIds(eventNodes);
      setCollapsedEvents(kTranscriptCollapseScope, allCollapsibleIds);
    }
  }, [
    defaultCollapsedIds,
    eventNodes,
    collapsed,
    setCollapsedEvents,
    events.length,
  ]);

  // ---------------------------------------------------------------------------
  // Outline state
  // ---------------------------------------------------------------------------

  const [outlineCollapsed, setOutlineCollapsed] = useProperty<boolean>(
    "timelineEvents",
    "outlineCollapsed",
    { defaultValue: !defaultOutlineExpanded, cleanup: false }
  );
  const isOutlineCollapsed = outlineCollapsed ?? !defaultOutlineExpanded;

  // Track whether the outline component reports displayable nodes.
  // When the outline is collapsed (unmounted), it can't report, so we
  // optimistically fall back to hasMatchingEvents to keep the toggle enabled.
  const [reportedHasNodes, setReportedHasNodes] = useState(true);
  const outlineHasNodes = isOutlineCollapsed
    ? hasMatchingEvents
    : reportedHasNodes;
  const [outlineWidth, setOutlineWidth] = useState<number | undefined>();
  const handleOutlineHasNodesChange = useCallback(
    (hasNodes: boolean) => {
      setReportedHasNodes(hasNodes);
      if (!hasNodes && !isOutlineCollapsed) {
        setOutlineCollapsed(true);
      }
    },
    [isOutlineCollapsed, setOutlineCollapsed]
  );

  // ---------------------------------------------------------------------------
  // Derived values
  // ---------------------------------------------------------------------------

  const showSwimlanes =
    timelineProp === true || (timelineProp === "auto" && hasTimeline);

  const scrollToTop = useCallback(() => {
    scrollRef.current?.scrollTo({ top: 0 });
  }, [scrollRef]);

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <TimelineSelectContext.Provider value={selectBySpanId}>
      <div className={clsx(styles.root, className)}>
        {showSwimlanes && (
          <StickyScroll
            scrollRef={scrollRef}
            offsetTop={offsetTop}
            zIndex={500}
            preserveHeight={true}
            onStickyChange={handleSwimLaneStickyChange}
          >
            <div ref={swimLaneStickyContentRef}>
              <TimelineSwimLanes
                layouts={timelineLayouts}
                timeline={timelineState}
                header={{
                  rootLabel: timelineData.root.name,
                  onScrollToTop: scrollToTop,
                  minimap: {
                    root: timelineData.root,
                    selection: minimapSelection,
                    mapping: rootTimeMapping,
                  },
                  timelineConfig,
                  timelineSelector:
                    timelines.length > 1
                      ? {
                          timelines,
                          activeIndex: activeTimelineIndex,
                          onSelect: setActiveTimeline,
                        }
                      : undefined,
                }}
                onMarkerNavigate={onMarkerNavigate}
                isSticky={isSwimLaneSticky}
              />
            </div>
          </StickyScroll>
        )}
        <div
          className={clsx(
            styles.eventsContainer,
            isOutlineCollapsed && styles.outlineCollapsed
          )}
          style={
            !isOutlineCollapsed && outlineWidth
              ? ({ "--outline-width": `${outlineWidth}px` } as CSSProperties)
              : undefined
          }
        >
          <StickyScroll
            scrollRef={scrollRef}
            className={styles.eventsOutline}
            offsetTop={offsetTop + stickySwimLaneHeight}
          >
            {!isOutlineCollapsed && (
              <TranscriptOutline
                eventNodes={eventNodes}
                defaultCollapsedIds={defaultCollapsedIds}
                scrollRef={scrollRef}
                onHasNodesChange={handleOutlineHasNodesChange}
                onWidthChange={setOutlineWidth}
                onNavigateToEvent={handleOutlineNavigate}
                scrollTrackOffset={offsetTop + stickySwimLaneHeight}
              />
            )}
            <button
              type="button"
              className={styles.outlineToggle}
              onClick={
                outlineHasNodes
                  ? () => setOutlineCollapsed(!isOutlineCollapsed)
                  : undefined
              }
              aria-disabled={!outlineHasNodes}
              title={
                outlineHasNodes
                  ? undefined
                  : "No outline available for the current filter"
              }
              aria-label={isOutlineCollapsed ? "Show outline" : "Hide outline"}
            >
              <i className={ApplicationIcons.sidebar} />
            </button>
          </StickyScroll>
          <div className={styles.eventsSeparator} />
          {hasMatchingEvents ? (
            <TranscriptViewNodes
              key={eventsListId}
              ref={eventsListRef}
              id={eventsListId}
              eventNodes={eventNodes}
              defaultCollapsedIds={defaultCollapsedIds}
              initialEventId={initialEventId}
              offsetTop={offsetTop + stickySwimLaneHeight}
              className={styles.eventsList}
              scrollRef={scrollRef}
            />
          ) : (
            <NoContentsPanel text="No events match the current filter" />
          )}
        </div>
      </div>
    </TimelineSelectContext.Provider>
  );
};
