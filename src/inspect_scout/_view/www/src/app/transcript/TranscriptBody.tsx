import clsx from "clsx";
import { FC, useRef } from "react";
import { useSearchParams } from "react-router-dom";

import { ChatViewVirtualList } from "../../chat/ChatViewVirtualList";
import { TabPanel, TabSet } from "../../components/TabSet";
import { MetaDataGrid } from "../../content/MetaDataGrid";
import { useStore } from "../../state/store";
import { TranscriptView } from "../../transcript/TranscriptView";
import { Transcript } from "../../types/api-types";

import styles from "./TranscriptBody.module.css";

const kTranscriptMessagesTabId = "transcript-messages";
const kTranscriptEventsTabId = "transcript-events";
const kTranscriptMetadataTabId = "transcript-metadata";

interface TranscriptBodyProps {
  transcript: Transcript;
}

export const TranscriptBody: FC<TranscriptBodyProps> = ({ transcript }) => {
  const messagesScrollRef = useRef<HTMLDivElement | null>(null);
  const [_searchParams, setSearchParams] = useSearchParams();

  const selectedTranscriptTab = useStore(
    (state) => state.selectedTranscriptTab
  );
  const setSelectedTranscriptTab = useStore(
    (state) => state.setSelectedTranscriptTab
  );
  const resolvedSelectedTranscriptTab =
    selectedTranscriptTab || kTranscriptMessagesTabId;

  // Helper function to update both store and URL
  const handleTabChange = (tabId: string) => {
    setSelectedTranscriptTab(tabId);
    setSearchParams({ tab: tabId });
  };
  return (
    <div className={clsx(styles.tabContainer)}>
      <TabSet
        id={"transcript-body"}
        type="pills"
        tabPanelsClassName={clsx(styles.tabSet)}
        tabControlsClassName={clsx(styles.tabControl)}
        className={clsx(styles.tabs)}
        tools={[]}
      >
        <TabPanel
          key={kTranscriptMessagesTabId}
          id={kTranscriptMessagesTabId}
          className={clsx(styles.chatTab)}
          title="Messages"
          onSelected={() => {
            handleTabChange(kTranscriptMessagesTabId);
          }}
          selected={resolvedSelectedTranscriptTab === kTranscriptMessagesTabId}
          scrollable={true}
        >
          <ChatViewVirtualList
            id={"transcript-id"}
            messages={transcript.messages || []}
            toolCallStyle={"complete"}
            indented={false}
            className={styles.chatList}
          />
        </TabPanel>
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
          <TranscriptView
            id={"transcript-events-list"}
            events={transcript.events || []}
          />
        </TabPanel>
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
          <MetaDataGrid
            id="transcript-metadata-grid"
            entries={transcript.metadata || {}}
          />
        </TabPanel>
      </TabSet>
    </div>
  );
};
