import { VscodeSplitLayout } from "@vscode-elements/react-elements";
import clsx from "clsx";
import {
  CSSProperties,
  FC,
  ReactNode,
  RefObject,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { ChatViewVirtualList } from "../../components/chat/ChatViewVirtualList";
import { DisplayModeContext } from "../../components/content/DisplayModeContext";
import { MetaDataGrid } from "../../components/content/MetaDataGrid";
import { ApplicationIcons } from "../../components/icons";
import { NoContentsPanel } from "../../components/NoContentsPanel";
import { StickyScroll } from "../../components/StickyScroll";
import { TabPanel, TabSet } from "../../components/TabSet";
import { ToolButton } from "../../components/ToolButton";
import { ToolDropdownButton } from "../../components/ToolDropdownButton";
import { useEventNodes } from "../../components/transcript/hooks/useEventNodes";
import { TranscriptOutline } from "../../components/transcript/outline/TranscriptOutline";
import { TimelineSelectContext } from "../../components/transcript/TimelineSelectContext";
import { TranscriptViewNodes } from "../../components/transcript/TranscriptViewNodes";
import {
  EventNode,
  kCollapsibleEventTypes,
  kTranscriptCollapseScope,
} from "../../components/transcript/types";
import { getValidationParam, updateValidationParam } from "../../router/url";
import { useStore } from "../../state/store";
import { Transcript } from "../../types/api-types";
import { TimelineSwimLanes } from "../timeline/components/TimelineSwimLanes";
import { buildSpanSelectKeys } from "../timeline/timelineEventNodes";
import { messagesToStr } from "../utils/messages";
import { ValidationCaseEditor } from "../validation/components/ValidationCaseEditor";

import { useTranscriptColumnFilter } from "./hooks/useTranscriptColumnFilter";
import { useTranscriptNavigation } from "./hooks/useTranscriptNavigation";
import { useTranscriptTimeline } from "./hooks/useTranscriptTimeline";
import styles from "./TranscriptBody.module.css";
import { TranscriptFilterPopover } from "./TranscriptFilterPopover";

export const kTranscriptMessagesTabId = "transcript-messages";
export const kTranscriptEventsTabId = "transcript-events";
export const kTranscriptMetadataTabId = "transcript-metadata";
export const kTranscriptInfoTabId = "transcript-info";

/**
 * Recursively collects all collapsible event IDs from the event tree.
 */
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

interface TranscriptBodyProps {
  transcript: Transcript;
  scrollRef: RefObject<HTMLDivElement | null>;
}

export const TranscriptBody: FC<TranscriptBodyProps> = ({
  transcript,
  scrollRef,
}) => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { getEventUrl } = useTranscriptNavigation();
  const tabParam = searchParams.get("tab");

  // Get event or message ID from query params for deep linking
  const eventParam = searchParams.get("event");
  const messageParam = searchParams.get("message");

  // Selected tab — default to Events when the transcript has events
  const hasEvents = transcript.events && transcript.events.length > 0;
  const defaultTab = hasEvents
    ? kTranscriptEventsTabId
    : kTranscriptMessagesTabId;
  const selectedTranscriptTab = useStore(
    (state) => state.selectedTranscriptTab
  );
  const setSelectedTranscriptTab = useStore(
    (state) => state.setSelectedTranscriptTab
  );
  const resolvedSelectedTranscriptTab =
    tabParam || selectedTranscriptTab || defaultTab;

  const handleTabChange = useCallback(
    (tabId: string) => {
      //  update both store and URL
      setSelectedTranscriptTab(tabId);
      setSearchParams((prevParams) => {
        const newParams = new URLSearchParams(prevParams);
        newParams.set("tab", tabId);
        // Clear deep link params so the auto-switch effect doesn't
        // fight the user's explicit tab choice
        newParams.delete("event");
        newParams.delete("message");
        return newParams;
      });
    },
    [setSelectedTranscriptTab, setSearchParams]
  );

  // Suppress swimlane collapse during programmatic scrolls (marker clicks).
  // The swimlane still goes sticky (opaque bg, fixed position) but stays expanded.
  //
  // We use a ref to signal "next sticky transition should not collapse" because
  // the scroll that triggers sticky happens synchronously during navigate(),
  // before React can process any state update from the click handler.
  // The ref is checked inside handleSwimLaneStickyChange (same tick as the
  // scroll event) and converted to state there, ensuring both isSwimLaneSticky
  // and markerNavSticky are set in the same callback → same React batch.
  const suppressCollapseRef = useRef(false);
  const [markerNavSticky, setMarkerNavSticky] = useState(false);

  // Navigate to a specific event when a marker is clicked on the timeline.
  const handleMarkerNavigate = useCallback(
    (eventId: string) => {
      const url = getEventUrl(eventId);
      if (!url) return;
      suppressCollapseRef.current = true;
      void navigate(url);
    },
    [getEventUrl, navigate]
  );

  // Auto-switch tab based on deep link params
  useEffect(() => {
    if (
      eventParam &&
      resolvedSelectedTranscriptTab !== kTranscriptEventsTabId
    ) {
      handleTabChange(kTranscriptEventsTabId);
    } else if (
      messageParam &&
      resolvedSelectedTranscriptTab !== kTranscriptMessagesTabId
    ) {
      handleTabChange(kTranscriptMessagesTabId);
    }
  }, [
    eventParam,
    messageParam,
    resolvedSelectedTranscriptTab,
    handleTabChange,
  ]);

  // Transcript Filtering
  const transcriptFilterButtonRef = useRef<HTMLButtonElement | null>(null);
  const [transcriptFilterShowing, setTranscriptFilterShowing] = useState(false);
  const toggleTranscriptFilterShowing = useCallback(() => {
    setTranscriptFilterShowing((prev) => !prev);
  }, []);
  const { excludedEventTypes, isDebugFilter, isDefaultFilter } =
    useTranscriptColumnFilter();

  // Pre-filter events by excluded types before feeding into the timeline pipeline
  const filteredEvents = useMemo(() => {
    if (excludedEventTypes.length === 0) return transcript.events;
    return transcript.events.filter(
      (event) => !excludedEventTypes.includes(event.event)
    );
  }, [transcript.events, excludedEventTypes]);

  // Timeline swimlanes pipeline
  const {
    timeline: timelineData,
    state: timelineState,
    layouts: timelineLayouts,
    rootTimeMapping,
    selectedEvents,
    sourceSpans,
    minimapSelection,
    hasTimeline,
  } = useTranscriptTimeline(filteredEvents);

  // Build a span-ID-aware navigation function for agent card clicks.
  // Maps each span's unique ID to the (name, spanIndex) pair that
  // the swimlane selection system expects. Parallel spans drill down
  // into the parallel container and select the specific instance.
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
        // Drill into the parallel container, select the specific instance.
        // After drill-down, the child row is named "<name> <spanIndex>".
        timelineDrillDownAndSelect(key.name, `${key.name} ${key.spanIndex}`);
      } else {
        timelineSelect(key.name, key.spanIndex);
      }
    },
    [spanSelectKeys, timelineSelect, timelineDrillDownAndSelect]
  );

  // Sticky swimlane state — when the swimlane scrolls past the tab bar,
  // it collapses and sticks below it.
  const [isSwimLaneSticky, setIsSwimLaneSticky] = useState(false);
  const [stickySwimLaneHeight, setStickySwimLaneHeight] = useState(0);
  const swimLaneStickyContentRef = useRef<HTMLDivElement | null>(null);

  const handleSwimLaneStickyChange = useCallback((sticky: boolean) => {
    setIsSwimLaneSticky(sticky);
    if (sticky && suppressCollapseRef.current) {
      // Consume the ref flag and promote to state in the same callback,
      // so React batches both setIsSwimLaneSticky(true) and
      // setMarkerNavSticky(true) into a single render.
      suppressCollapseRef.current = false;
      setMarkerNavSticky(true);
    } else if (!sticky) {
      setStickySwimLaneHeight(0);
      setMarkerNavSticky(false);
    }
  }, []);

  // Measure the sticky swimlane height via ResizeObserver so the outline
  // offset updates reliably after the swimlane collapses/expands.
  useEffect(() => {
    const el = swimLaneStickyContentRef.current;
    if (!isSwimLaneSticky || !el) {
      return;
    }
    const observer = new ResizeObserver(() => {
      setStickySwimLaneHeight(el.getBoundingClientRect().height);
    });
    observer.observe(el);
    // Initial measurement
    setStickySwimLaneHeight(el.getBoundingClientRect().height);
    return () => observer.disconnect();
  }, [isSwimLaneSticky]);

  // Transcript event data
  const { eventNodes, defaultCollapsedIds } = useEventNodes(
    selectedEvents,
    false,
    sourceSpans
  );
  const hasMatchingEvents = eventNodes.length > 0;

  // Reset scroll position when the selected events change (e.g. clicking a
  // different swimlane bar). Skip when an event deep-link is active since the
  // virtual list handles scroll-to-event in that case.
  useEffect(() => {
    if (!eventParam) {
      scrollRef.current?.scrollTo({ top: 0 });
    }
  }, [selectedEvents, eventParam, scrollRef]);

  // Transcript collapse
  const eventsCollapsed = useStore((state) => state.transcriptState.collapsed);
  const setTranscriptState = useStore((state) => state.setTranscriptState);
  const collapseEvents = useCallback(
    (collapsed: boolean) => {
      setTranscriptState((prev) => ({
        ...prev,
        collapsed,
      }));
    },
    [setTranscriptState]
  );

  const setCollapsedEvents = useStore(
    (state) => state.setTranscriptCollapsedEvents
  );

  // Outline toggle
  const outlineCollapsed = useStore(
    (state) => state.transcriptState.outlineCollapsed
  );
  const toggleOutline = useCallback(
    (collapsed: boolean) => {
      setTranscriptState((prev) => ({
        ...prev,
        outlineCollapsed: collapsed,
      }));
    },
    [setTranscriptState]
  );

  // Track whether the outline has displayable nodes (reported by TranscriptOutline)
  const [outlineHasNodes, setOutlineHasNodes] = useState(true);
  const [outlineWidth, setOutlineWidth] = useState<number | undefined>();
  const handleOutlineHasNodesChange = useCallback(
    (hasNodes: boolean) => {
      setOutlineHasNodes(hasNodes);
      if (!hasNodes && !outlineCollapsed) {
        toggleOutline(true);
      }
    },
    [outlineCollapsed, toggleOutline]
  );

  // When the outline is collapsed (unmounted), it can't report node changes.
  // Optimistically re-enable the toggle when eventNodes change so the user
  // can reopen the outline, which will then re-validate via onHasNodesChange.
  // When there are no matching events, definitively disable the toggle.
  useEffect(() => {
    if (outlineCollapsed) {
      setOutlineHasNodes(hasMatchingEvents);
    }
  }, [outlineCollapsed, hasMatchingEvents, eventNodes]);

  // Validation sidebar - URL is the source of truth
  const validationSidebarCollapsed = !getValidationParam(searchParams);

  const toggleValidationSidebar = useCallback(() => {
    setSearchParams((prevParams) => {
      const isCurrentlyOpen = getValidationParam(prevParams);
      return updateValidationParam(prevParams, !isCurrentlyOpen);
    });
  }, [setSearchParams]);

  // Display mode for raw/rendered text
  const displayMode = useStore(
    (state) => state.transcriptState.displayMode ?? "rendered"
  );

  const toggleDisplayMode = useCallback(() => {
    setTranscriptState((prev) => ({
      ...prev,
      displayMode: prev.displayMode === "raw" ? "rendered" : "raw",
    }));
  }, [setTranscriptState]);

  const displayModeContextValue = useMemo(
    () => ({ displayMode }),
    [displayMode]
  );

  useEffect(() => {
    if (transcript.events.length <= 0 || eventsCollapsed === undefined) {
      return;
    }

    if (!eventsCollapsed && Object.keys(defaultCollapsedIds).length > 0) {
      setCollapsedEvents(kTranscriptCollapseScope, defaultCollapsedIds);
    } else if (eventsCollapsed) {
      const allCollapsibleIds = collectAllCollapsibleIds(eventNodes);
      setCollapsedEvents(kTranscriptCollapseScope, allCollapsibleIds);
    }
  }, [
    defaultCollapsedIds,
    eventNodes,
    eventsCollapsed,
    setCollapsedEvents,
    transcript.events.length,
  ]);

  const tabTools: ReactNode[] = [];

  if (resolvedSelectedTranscriptTab === kTranscriptEventsTabId) {
    const label = isDebugFilter
      ? "Debug"
      : isDefaultFilter
        ? "Default"
        : "Custom";

    tabTools.push(
      <ToolButton
        key="events-filter-transcript"
        label={`Events: ${label}`}
        icon={ApplicationIcons.filter}
        onClick={toggleTranscriptFilterShowing}
        className={styles.tabTool}
        subtle={true}
        ref={transcriptFilterButtonRef}
      />
    );

    tabTools.push(
      <ToolButton
        key="event-collapse-transcript"
        label={eventsCollapsed ? "Expand" : "Collapse"}
        icon={
          eventsCollapsed
            ? ApplicationIcons.expand.all
            : ApplicationIcons.collapse.all
        }
        onClick={() => {
          collapseEvents(!eventsCollapsed);
        }}
        subtle={true}
      />
    );
  }

  tabTools.push(
    <ToolButton
      key="display-mode-toggle"
      label={displayMode === "rendered" ? "Raw" : "Rendered"}
      icon={ApplicationIcons.display}
      onClick={toggleDisplayMode}
      className={styles.tabTool}
      subtle={true}
      title={
        displayMode === "rendered"
          ? "Show raw text without markdown rendering"
          : "Show rendered markdown"
      }
    />
  );

  tabTools.push(
    <CopyToolbarButton transcript={transcript} className={styles.tabTool} />
  );

  tabTools.push(
    <ToolButton
      key="validation-sidebar-toggle"
      label="Validation"
      icon={ApplicationIcons.edit}
      onClick={toggleValidationSidebar}
      className={styles.tabTool}
      subtle={true}
      title={
        validationSidebarCollapsed
          ? "Show validation editor"
          : "Hide validation editor"
      }
    />
  );

  const atRoot = timelineState.breadcrumbs.length <= 1;

  const scrollToTop = useCallback(() => {
    scrollRef.current?.scrollTo({ top: 0 });
  }, [scrollRef]);

  const messagesPanel = (
    <TabPanel
      key={kTranscriptMessagesTabId}
      id={kTranscriptMessagesTabId}
      className={clsx(styles.chatTab)}
      title="Messages"
      onSelected={() => {
        handleTabChange(kTranscriptMessagesTabId);
      }}
      selected={resolvedSelectedTranscriptTab === kTranscriptMessagesTabId}
      scrollable={false}
    >
      <ChatViewVirtualList
        id={"transcript-id"}
        messages={transcript.messages || []}
        initialMessageId={messageParam}
        toolCallStyle={"complete"}
        indented={false}
        className={styles.chatList}
        scrollRef={scrollRef}
        showLabels={true}
      />
    </TabPanel>
  );

  const eventsPanel = hasEvents ? (
    <TabPanel
      key="transcript-events"
      id={kTranscriptEventsTabId}
      className={clsx(styles.eventsTab)}
      title="Events"
      onSelected={() => {
        handleTabChange(kTranscriptEventsTabId);
      }}
      selected={resolvedSelectedTranscriptTab === kTranscriptEventsTabId}
      scrollable={false}
    >
      <TimelineSelectContext.Provider value={selectBySpanId}>
        <div className={styles.eventsTabContent}>
          {hasTimeline && timelineData && (
            <StickyScroll
              scrollRef={scrollRef}
              offsetTop={40}
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
                  onMarkerNavigate={handleMarkerNavigate}
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
              outlineCollapsed && styles.outlineCollapsed
            )}
            style={
              !outlineCollapsed && outlineWidth
                ? ({ "--outline-width": `${outlineWidth}px` } as CSSProperties)
                : undefined
            }
          >
            <StickyScroll
              scrollRef={scrollRef}
              className={styles.eventsOutline}
              offsetTop={40 + stickySwimLaneHeight}
            >
              {!outlineCollapsed && (
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
                    ? () => toggleOutline(!outlineCollapsed)
                    : undefined
                }
                aria-disabled={!outlineHasNodes}
                title={
                  outlineHasNodes
                    ? undefined
                    : "No outline available for the current filter"
                }
                aria-label={outlineCollapsed ? "Show outline" : "Hide outline"}
              >
                <i className={ApplicationIcons.sidebar} />
              </button>
            </StickyScroll>
            <div className={styles.eventsSeparator} />
            {hasMatchingEvents ? (
              <TranscriptViewNodes
                id={"transcript-events-list"}
                eventNodes={eventNodes}
                defaultCollapsedIds={defaultCollapsedIds}
                initialEventId={eventParam}
                offsetTop={40 + stickySwimLaneHeight}
                className={styles.eventsList}
                scrollRef={scrollRef}
              />
            ) : (
              <NoContentsPanel text="No events match the current filter" />
            )}
          </div>
        </div>
      </TimelineSelectContext.Provider>
      <TranscriptFilterPopover
        showing={transcriptFilterShowing}
        setShowing={setTranscriptFilterShowing}
        // eslint-disable-next-line react-hooks/refs -- positionEl accepts null; PopOver/Popper handles this in effects and updates when ref is populated
        positionEl={transcriptFilterButtonRef.current}
      />
    </TabPanel>
  ) : null;

  // Events tab first when available, then Messages
  const tabPanels = [...(eventsPanel ? [eventsPanel] : []), messagesPanel];

  if (transcript.metadata && Object.keys(transcript.metadata).length > 0) {
    tabPanels.push(
      <TabPanel
        key="transcript-metadata"
        id={kTranscriptMetadataTabId}
        className={clsx(styles.metadataTab)}
        title="Metadata"
        onSelected={() => {
          handleTabChange(kTranscriptMetadataTabId);
        }}
        selected={resolvedSelectedTranscriptTab === kTranscriptMetadataTabId}
        scrollable={false}
      >
        <div className={styles.scrollable}>
          <MetaDataGrid
            id="transcript-metadata-grid"
            entries={transcript.metadata || {}}
            className={clsx(styles.metadata)}
          />
        </div>
      </TabPanel>
    );
  }

  const { events, messages, metadata, ...infoData } = transcript;
  tabPanels.push(
    <TabPanel
      key="transcript-info"
      id={kTranscriptInfoTabId}
      className={clsx(styles.infoTab)}
      title="Info"
      onSelected={() => {
        handleTabChange(kTranscriptInfoTabId);
      }}
      selected={resolvedSelectedTranscriptTab === kTranscriptInfoTabId}
      scrollable={false}
    >
      <div className={styles.scrollable}>
        <MetaDataGrid
          id="transcript-info-grid"
          entries={infoData}
          className={clsx(styles.metadata)}
        />
      </div>
    </TabPanel>
  );

  const tabSetContent = (
    <TabSet
      id={"transcript-body"}
      type="pills"
      tabPanelsClassName={clsx(styles.tabSet)}
      tabControlsClassName={clsx(styles.tabControl)}
      className={clsx(styles.tabs)}
      tools={tabTools}
    >
      {tabPanels}
    </TabSet>
  );

  return (
    <DisplayModeContext.Provider value={displayModeContextValue}>
      {validationSidebarCollapsed ? (
        tabSetContent
      ) : (
        <VscodeSplitLayout
          className={styles.splitLayout}
          fixedPane="end"
          initialHandlePosition="80%"
          minEnd="180px"
          minStart="200px"
        >
          <div slot="start" className={styles.splitStart}>
            {tabSetContent}
          </div>
          <div slot="end" className={styles.validationSidebar}>
            <ValidationCaseEditor transcriptId={transcript.transcript_id} />
          </div>
        </VscodeSplitLayout>
      )}
    </DisplayModeContext.Provider>
  );
};

const CopyToolbarButton: FC<{
  transcript: Transcript;
  className?: string | string[];
}> = ({ transcript, className }) => {
  const [icon, setIcon] = useState<string>(ApplicationIcons.copy);

  const showCopyConfirmation = useCallback(() => {
    setIcon(ApplicationIcons.confirm);
    setTimeout(() => setIcon(ApplicationIcons.copy), 1250);
  }, []);

  if (!transcript) {
    return undefined;
  }

  return (
    <ToolDropdownButton
      key="sample-copy"
      label="Copy"
      icon={icon}
      className={clsx(className)}
      dropdownClassName={"text-size-smallest"}
      dropdownAlign="right"
      subtle={true}
      items={{
        UUID: () => {
          if (transcript.transcript_id) {
            void navigator.clipboard.writeText(transcript.transcript_id);
            showCopyConfirmation();
          }
        },
        Transcript: () => {
          if (transcript.messages) {
            void navigator.clipboard.writeText(
              messagesToStr(transcript.messages)
            );
            showCopyConfirmation();
          }
        },
      }}
    />
  );
};
