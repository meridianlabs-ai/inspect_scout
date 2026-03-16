import clsx from "clsx";
import {
  CSSProperties,
  FC,
  RefObject,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import { ApplicationIcons } from "../../../components/icons";
import { NoContentsPanel } from "../../../components/NoContentsPanel";
import { StickyScroll } from "../../../components/StickyScroll";
import { useEventNodes } from "../../../components/transcript/hooks/useEventNodes";
import { TranscriptOutline } from "../../../components/transcript/outline/TranscriptOutline";
import { resolveMessageToEvent } from "../../../components/transcript/resolveMessageToEvent";
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
import type { Event, ServerTimeline } from "../../../types/api-types";
import { useScrubberProgress } from "../hooks/useScrubberPercent";
import type { TimelineOptions } from "../hooks/useTimeline";
import { useTimelineConfig } from "../hooks/useTimelineConfig";
import { useTranscriptTimeline } from "../hooks/useTranscriptTimeline";
import {
  buildSpanSelectKeys,
  getSelectedSpans,
  parseSelection,
} from "../timelineEventNodes";
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
  /** Deep-link to a message ID, resolved to the best matching event. */
  initialMessageId?: string | null;
  /** Initial outline state when no persistent preference exists. Default: false (collapsed). */
  defaultOutlineExpanded?: boolean;
  /** Unique ID for the virtual list. */
  id: string;
  /** Bulk collapse/expand of all collapsible events. undefined = no-op. */
  collapsed?: boolean;
  /** Called when a marker (error, compaction) is clicked on the swimlane.
   *  Optional `selectedKey` requests the bar be selected atomically with navigation. */
  onMarkerNavigate?: (eventId: string, selectedKey?: string) => void;
  /** Controls which marker kinds are shown and at what depth. */
  markerConfig?: MarkerConfig;
  /** Controls swimlane visibility. `"auto"` shows when data has child spans. Default: `"auto"`. */
  timeline?: true | false | "auto";
  /** Controls which agents are included in the timeline. */
  agentConfig?: TimelineOptions;
  /** Server-provided timelines (used when available instead of building from events). */
  timelines?: ServerTimeline[];
  /** Headroom direction signal: true = scrolling down (hide). */
  headroomHidden?: boolean;
  /** Reset the headroom anchor before a layout shift or programmatic scroll.
   *  Pass `true` to debounce (keeps lock alive while scrolling continues). */
  onHeadroomResetAnchor?: (debounce?: boolean) => void;
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
  initialMessageId,
  defaultOutlineExpanded = false,
  id,
  collapsed,
  onMarkerNavigate,
  markerConfig,
  timeline: timelineProp = "auto",
  agentConfig,
  timelines: serverTimelines,
  headroomHidden,
  onHeadroomResetAnchor,
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
    regionCounts,
  } = useTranscriptTimeline(
    events,
    resolvedMarkerConfig,
    resolvedAgentConfig,
    serverTimelines
  );

  // ---------------------------------------------------------------------------
  // Scroll-resetting selection wrappers
  // ---------------------------------------------------------------------------
  //
  // Every user-initiated selection change (swimlane click, agent card click,
  // breadcrumb) flows through these wrappers. They imperatively clear the
  // saved Virtuoso state and scroll to top *before* the URL update, so the
  // new Virtuoso instance mounts into a clean scroll position.

  const clearListPosition = useStore((state) => state.clearListPosition);
  const clearListPositionsWithPrefix = useStore(
    (state) => state.clearListPositionsWithPrefix
  );

  const resetScrollForSelection = useCallback(
    (nextKey: string | null) => {
      // Clear saved Virtuoso state for the target agent
      const nextListId = nextKey ? `${id}:${nextKey}` : id;
      clearListPosition(`live-virtual-list-${nextListId}`);

      // When navigating "up" in breadcrumbs, also discard child positions
      const currentSelected = timelineState.selected;
      if (
        nextKey &&
        currentSelected &&
        currentSelected.startsWith(nextKey + "/")
      ) {
        clearListPositionsWithPrefix(`live-virtual-list-${id}:${nextKey}/`);
      }

      scrollRef.current?.scrollTo({ top: 0 });
    },
    [
      id,
      scrollRef,
      timelineState.selected,
      clearListPosition,
      clearListPositionsWithPrefix,
    ]
  );

  const { select: rawSelect, clearSelection: rawClearSelection } =
    timelineState;

  const select = useCallback(
    (key: string | null) => {
      resetScrollForSelection(key);
      rawSelect(key);
    },
    [resetScrollForSelection, rawSelect]
  );

  const clearSelection = useCallback(() => {
    resetScrollForSelection(null);
    rawClearSelection();
  }, [resetScrollForSelection, rawClearSelection]);

  // TimelineState with scroll-resetting select/clearSelection for swimlanes
  const patchedTimelineState = useMemo(
    () => ({ ...timelineState, select, clearSelection }),
    [timelineState, select, clearSelection]
  );

  // ---------------------------------------------------------------------------
  // Span selection context (agent card clicks → swimlane selection)
  // ---------------------------------------------------------------------------

  const spanSelectKeys = useMemo(
    () => buildSpanSelectKeys(timelineState.rows),
    [timelineState.rows]
  );
  const selectBySpanId = useCallback(
    (spanId: string) => {
      const key = spanSelectKeys.get(spanId);
      if (!key) return;
      select(key.key);
    },
    [spanSelectKeys, select]
  );

  // ---------------------------------------------------------------------------
  // Message ID → event resolution
  // ---------------------------------------------------------------------------

  // Resolve message ID against the selected span first, then fall back to root.
  const resolvedLocal = useMemo(() => {
    if (initialEventId || !initialMessageId) return undefined;
    const selectedSpans = getSelectedSpans(
      timelineState.rows,
      timelineState.selected
    );
    for (const span of selectedSpans) {
      const result = resolveMessageToEvent(initialMessageId, span);
      if (result && !result.agentSpanId) return result;
    }
    return undefined;
  }, [
    initialEventId,
    initialMessageId,
    timelineState.rows,
    timelineState.selected,
  ]);

  const resolvedRoot = useMemo(() => {
    if (initialEventId || !initialMessageId || resolvedLocal) return undefined;
    const result = resolveMessageToEvent(initialMessageId, timelineData.root);
    return result;
  }, [initialEventId, initialMessageId, resolvedLocal, timelineData.root]);

  const resolved = resolvedLocal ?? resolvedRoot;

  // Side-effect: navigate to the correct swimlane when resolution came from root
  useEffect(() => {
    if (!resolvedRoot) return;
    if (resolvedRoot.agentSpanId) {
      selectBySpanId(resolvedRoot.agentSpanId);
    } else if (timelineState.selected) {
      clearSelection();
    }
  }, [resolvedRoot, selectBySpanId, clearSelection, timelineState.selected]);

  const effectiveInitialEventId = initialEventId ?? resolved?.eventId ?? null;

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
  const handleOutlineNavigate = useCallback(
    (eventId: string) => {
      // Suppress headroom direction changes during the programmatic scroll
      // so the swimlane header doesn't collapse/reveal mid-animation.
      onHeadroomResetAnchor?.(true);
      eventsListRef.current?.scrollToEvent(eventId);
    },
    [onHeadroomResetAnchor]
  );

  // Per-agent scroll position persistence using Virtuoso StateSnapshot.
  // Each agent gets its own Virtuoso instance (via React `key`) so that
  // item measurements and scroll position are preserved independently.
  // Scroll reset is handled imperatively by the selection wrappers above.
  const selected = timelineState.selected;
  const eventsListId = selected ? `${id}:${selected}` : id;

  // Scrubber scroll progress (0–1) for the minimap
  const listKey = `live-virtual-list-${eventsListId}`;
  const scrubberProgress = useScrubberProgress(listKey);

  const getVisibleRange = useStore((state) => state.getVisibleRange);

  const handleScrub = useCallback(
    (progress: number) => {
      const { totalCount } = getVisibleRange(listKey);
      if (totalCount <= 1) return;
      // Map progress (0–1) directly to a list index. scrollToIndex with
      // align:"start" naturally clamps at the bottom of the list, so we
      // don't need to subtract viewport size (which varies with item height).
      const targetIndex = Math.round(progress * (totalCount - 1));
      // Suppress headroom direction changes during programmatic scroll
      // so the swimlane header doesn't collapse/reveal while scrubbing.
      onHeadroomResetAnchor?.(true);
      eventsListRef.current?.scrollToIndex(targetIndex);
    },
    [getVisibleRange, listKey, onHeadroomResetAnchor]
  );

  // Clean up per-agent state when the transcript panel unmounts
  // (e.g. navigating to a different transcript).
  const clearTranscriptOutlineId = useStore(
    (state) => state.clearTranscriptOutlineId
  );

  useEffect(() => {
    const prefix = `live-virtual-list-${id}:`;
    return () => {
      clearListPositionsWithPrefix(prefix);
      clearTranscriptOutlineId();
    };
  }, [id, clearListPositionsWithPrefix, clearTranscriptOutlineId]);

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
  const userOutlineCollapsed = outlineCollapsed ?? !defaultOutlineExpanded;

  // Track whether the outline component reports displayable nodes.
  // When the outline is collapsed (unmounted), it can't report, so we
  // optimistically fall back to hasMatchingEvents to keep the toggle enabled.
  const [reportedHasNodes, setReportedHasNodes] = useState(true);

  // Reset to optimistic when eventNodes change (e.g. agent selection changes).
  // This lets the outline mount, discover its nodes, and report back.
  // Uses "adjust state during render" pattern to avoid an extra effect cycle.
  const [prevEventNodes, setPrevEventNodes] = useState(eventNodes);
  if (prevEventNodes !== eventNodes) {
    setPrevEventNodes(eventNodes);
    if (!reportedHasNodes) {
      setReportedHasNodes(true);
    }
  }

  // Auto-hide the outline when content has no nodes (e.g. utility agent)
  // without touching the user's persistent preference. When the user navigates
  // back to an agent with outline content, the preference is still intact.
  const autoHidden = !reportedHasNodes && !userOutlineCollapsed;
  const isOutlineCollapsed = userOutlineCollapsed || autoHidden;

  const outlineHasNodes = isOutlineCollapsed
    ? hasMatchingEvents
    : reportedHasNodes;
  const [outlineWidth, setOutlineWidth] = useState<number | undefined>();
  const handleOutlineHasNodesChange = useCallback((hasNodes: boolean) => {
    setReportedHasNodes(hasNodes);
  }, []);

  // ---------------------------------------------------------------------------
  // Derived values
  // ---------------------------------------------------------------------------

  // Compute the agent name for the outline header.
  // When a swimlane row is selected, show its name; otherwise show the root.
  const outlineAgentName = useMemo(() => {
    if (!timelineState.selected) return timelineData.root.name;
    // For iterative rows, selected includes a span index suffix (e.g.
    // "transcript/explore:0"). Parse it to get the base row key.
    const parsed = parseSelection(timelineState.selected);
    const rowKey = parsed?.rowKey ?? timelineState.selected;
    const row = timelineState.rows.find((r) => r.key === rowKey);
    return row?.name ?? timelineData.root.name;
  }, [timelineState.selected, timelineState.rows, timelineData.root.name]);

  const showSwimlanes = timelineProp !== false;
  const swimlanesDefaultCollapsed =
    timelineProp === "auto" && !hasTimeline && regionCounts.size === 0
      ? true
      : undefined;

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
                timeline={patchedTimelineState}
                header={{
                  rootLabel: timelineData.root.name,
                  onScrollToTop: scrollToTop,
                  minimap: {
                    root: timelineData.root,
                    selection: minimapSelection,
                    mapping: rootTimeMapping,
                    scrubberProgress,
                    onScrub: handleScrub,
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
                headroomCollapsed={!!headroomHidden && isSwimLaneSticky}
                onLayoutShift={onHeadroomResetAnchor}
                regionCounts={regionCounts}
                defaultCollapsed={swimlanesDefaultCollapsed}
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
            {
              ...(!isOutlineCollapsed && outlineWidth
                ? { "--outline-width": `${outlineWidth}px` }
                : undefined),
              "--outline-top": `${offsetTop + stickySwimLaneHeight}px`,
            } as CSSProperties
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
                agentName={outlineAgentName}
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
              initialEventId={effectiveInitialEventId}
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
