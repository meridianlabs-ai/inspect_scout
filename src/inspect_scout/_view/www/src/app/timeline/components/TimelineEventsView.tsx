import clsx from "clsx";
import {
  CSSProperties,
  RefObject,
  forwardRef,
  useCallback,
  useEffect,
  useImperativeHandle,
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
import { TranscriptViewNodes } from "../../../components/transcript/TranscriptViewNodes";
import {
  EventNode,
  kCollapsibleEventTypes,
  kTranscriptCollapseScope,
} from "../../../components/transcript/types";
import { useProperty } from "../../../state/hooks/useProperty";
import { useStore } from "../../../state/store";
import type { Event } from "../../../types/api-types";
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
  className?: string;
}

/** Imperative handle for parent to suppress swimlane collapse during programmatic scrolls. */
export interface TimelineEventsViewHandle {
  suppressNextCollapse: () => void;
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

export const TimelineEventsView = forwardRef<
  TimelineEventsViewHandle,
  TimelineEventsViewProps
>(function TimelineEventsView(
  {
    events,
    scrollRef,
    offsetTop = 0,
    initialEventId,
    defaultOutlineExpanded = false,
    id,
    collapsed,
    onMarkerNavigate,
    markerConfig,
    className,
  },
  ref
) {
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
  } = useTranscriptTimeline(events, markerConfig);

  // ---------------------------------------------------------------------------
  // Span selection context (agent card clicks → swimlane selection)
  // ---------------------------------------------------------------------------

  const spanSelectKeys = useMemo(
    () => buildSpanSelectKeys(timelineState.rows),
    [timelineState.rows]
  );
  const {
    select: timelineSelect,
    drillDownAndSelect: timelineDrillDownAndSelect,
  } = timelineState;
  const selectBySpanId = useCallback(
    (spanId: string) => {
      const key = spanSelectKeys.get(spanId);
      if (!key) return;
      if (key.parallel && key.spanIndex) {
        timelineDrillDownAndSelect(key.name, `${key.name} ${key.spanIndex}`);
      } else {
        timelineSelect(key.name, key.spanIndex);
      }
    },
    [spanSelectKeys, timelineSelect, timelineDrillDownAndSelect]
  );

  // ---------------------------------------------------------------------------
  // Sticky swimlane state
  // ---------------------------------------------------------------------------

  const suppressCollapseRef = useRef(false);
  const [markerNavSticky, setMarkerNavSticky] = useState(false);
  const [isSwimLaneSticky, setIsSwimLaneSticky] = useState(false);
  const [stickySwimLaneHeight, setStickySwimLaneHeight] = useState(0);
  const swimLaneStickyContentRef = useRef<HTMLDivElement | null>(null);

  useImperativeHandle(
    ref,
    () => ({
      suppressNextCollapse: () => {
        suppressCollapseRef.current = true;
      },
    }),
    []
  );

  const handleSwimLaneStickyChange = useCallback((sticky: boolean) => {
    setIsSwimLaneSticky(sticky);
    if (sticky && suppressCollapseRef.current) {
      suppressCollapseRef.current = false;
      setMarkerNavSticky(true);
    } else if (!sticky) {
      setStickySwimLaneHeight(0);
      setMarkerNavSticky(false);
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

  // Reset scroll position when the selected events change.
  // Skip when a deep-link is active.
  useEffect(() => {
    if (!initialEventId) {
      scrollRef.current?.scrollTo({ top: 0 });
    }
  }, [selectedEvents, initialEventId, scrollRef]);

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

  const atRoot = timelineState.breadcrumbs.length <= 1;

  const scrollToTop = useCallback(() => {
    scrollRef.current?.scrollTo({ top: 0 });
  }, [scrollRef]);

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <TimelineSelectContext.Provider value={selectBySpanId}>
      <div className={clsx(styles.root, className)}>
        {hasTimeline && timelineData && (
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
                  breadcrumbs: timelineState.breadcrumbs,
                  atRoot,
                  onNavigate: timelineState.navigateTo,
                  onScrollToTop: scrollToTop,
                  minimap: {
                    root: timelineData.root,
                    selection: minimapSelection,
                    mapping: rootTimeMapping,
                  },
                }}
                onMarkerNavigate={onMarkerNavigate}
                isSticky={isSwimLaneSticky}
                forceCollapsed={isSwimLaneSticky && !markerNavSticky}
                noAnimation={isSwimLaneSticky && !markerNavSticky}
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
              id={id}
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
});
