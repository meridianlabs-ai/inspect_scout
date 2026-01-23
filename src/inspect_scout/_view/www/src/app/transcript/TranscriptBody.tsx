import { VscodeSplitLayout } from "@vscode-elements/react-elements";
import clsx from "clsx";
import {
  FC,
  ReactNode,
  RefObject,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { useSearchParams } from "react-router-dom";

import { ChatViewVirtualList } from "../../components/chat/ChatViewVirtualList";
import { DisplayModeContext } from "../../components/content/DisplayModeContext";
import { MetaDataGrid } from "../../components/content/MetaDataGrid";
import { ApplicationIcons } from "../../components/icons";
import { StickyScroll } from "../../components/StickyScroll";
import { TabPanel, TabSet } from "../../components/TabSet";
import { ToolButton } from "../../components/ToolButton";
import { ToolDropdownButton } from "../../components/ToolDropdownButton";
import { useEventNodes } from "../../components/transcript/hooks/useEventNodes";
import { TranscriptOutline } from "../../components/transcript/outline/TranscriptOutline";
import { TranscriptViewNodes } from "../../components/transcript/TranscriptViewNodes";
import {
  EventNode,
  kCollapsibleEventTypes,
  kTranscriptCollapseScope,
} from "../../components/transcript/types";
import { getValidationParam, updateValidationParam } from "../../router/url";
import { useStore } from "../../state/store";
import { Transcript } from "../../types/api-types";
import { messagesToStr } from "../utils/messages";
import { ValidationCaseEditor } from "../validation/components/ValidationCaseEditor";

import { useTranscriptColumnFilter } from "./hooks/useTranscriptColumnFilter";
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
  const [searchParams, setSearchParams] = useSearchParams();
  const tabParam = searchParams.get("tab");

  // Get event or message ID from query params for deep linking
  const eventParam = searchParams.get("event");
  const messageParam = searchParams.get("message");

  // Selected tab
  const selectedTranscriptTab = useStore(
    (state) => state.selectedTranscriptTab
  );
  const setSelectedTranscriptTab = useStore(
    (state) => state.setSelectedTranscriptTab
  );
  const resolvedSelectedTranscriptTab =
    tabParam || selectedTranscriptTab || kTranscriptMessagesTabId;

  const handleTabChange = useCallback(
    (tabId: string) => {
      //  update both store and URL
      setSelectedTranscriptTab(tabId);
      setSearchParams((prevParams) => {
        const newParams = new URLSearchParams(prevParams);
        newParams.set("tab", tabId);
        return newParams;
      });
    },
    [setSelectedTranscriptTab, setSearchParams]
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

  const filteredEvents = useMemo(() => {
    if (excludedEventTypes.length === 0) {
      return transcript.events;
    }
    return transcript.events.filter((event) => {
      return !excludedEventTypes.includes(event.event);
    });
  }, [transcript.events, excludedEventTypes]);

  // Transcript event data
  const { eventNodes, defaultCollapsedIds } = useEventNodes(
    filteredEvents,
    false
  );

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

  const tabPanels = [
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
    </TabPanel>,
  ];

  if (transcript.events && transcript.events.length > 0) {
    tabPanels.push(
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
        <div
          className={clsx(
            styles.eventsContainer,
            outlineCollapsed ? styles.outlineCollapsed : undefined
          )}
        >
          <StickyScroll
            scrollRef={scrollRef}
            className={styles.eventsOutline}
            offsetTop={40}
          >
            {!outlineCollapsed && (
              <TranscriptOutline
                eventNodes={eventNodes}
                defaultCollapsedIds={defaultCollapsedIds}
                scrollRef={scrollRef}
              />
            )}
            <div
              className={styles.outlineToggle}
              onClick={() => toggleOutline(!outlineCollapsed)}
            >
              <i className={ApplicationIcons.sidebar} />
            </div>
          </StickyScroll>
          <div className={styles.eventsSeparator} />
          <TranscriptViewNodes
            id={"transcript-events-list"}
            eventNodes={eventNodes}
            defaultCollapsedIds={defaultCollapsedIds}
            initialEventId={eventParam}
            className={styles.eventsList}
            scrollRef={scrollRef}
          />
        </div>
        <TranscriptFilterPopover
          showing={transcriptFilterShowing}
          setShowing={setTranscriptFilterShowing}
          positionEl={transcriptFilterButtonRef.current}
        />
      </TabPanel>
    );
  }

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
