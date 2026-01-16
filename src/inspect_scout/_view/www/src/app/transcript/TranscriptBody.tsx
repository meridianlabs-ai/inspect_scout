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
import { useStore } from "../../state/store";
import { Transcript } from "../../types/api-types";
import { messagesToStr } from "../utils/messages";

import styles from "./TranscriptBody.module.css";
import { TranscriptFilterPopover } from "./TranscriptFilterPopover";
import { useTranscriptColumnFilter } from "./useTranscriptColumnFilter";

const kTranscriptMessagesTabId = "transcript-messages";
const kTranscriptEventsTabId = "transcript-events";
const kTranscriptMetadataTabId = "transcript-metadata";

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

  // Selected tab
  const selectedTranscriptTab = useStore(
    (state) => state.selectedTranscriptTab
  );
  const setSelectedTranscriptTab = useStore(
    (state) => state.setSelectedTranscriptTab
  );
  const resolvedSelectedTranscriptTab =
    tabParam || selectedTranscriptTab || kTranscriptMessagesTabId;

  const handleTabChange = (tabId: string) => {
    //  update both store and URL
    setSelectedTranscriptTab(tabId);
    setSearchParams({ tab: tabId });
  };

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
    <CopyToolbarButton transcript={transcript} className={styles.tabTool} />
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
        toolCallStyle={"complete"}
        indented={false}
        className={styles.chatList}
        scrollRef={scrollRef}
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

  return (
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
