import clsx from "clsx";
import { FC } from "react";
import { useSearchParams } from "react-router-dom";

import { ChatViewVirtualList } from "../../chat/ChatViewVirtualList";
import { MetaDataGrid } from "../../components/content/MetaDataGrid";
import { TabPanel, TabSet } from "../../components/TabSet";
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
  const [searchParams, setSearchParams] = useSearchParams();

  const selectedTranscriptTab = useStore(
    (state) => state.selectedTranscriptTab
  );
  const setSelectedTranscriptTab = useStore(
    (state) => state.setSelectedTranscriptTab
  );
  const tabParam = searchParams.get("tab");
  const resolvedSelectedTranscriptTab =
    tabParam || selectedTranscriptTab || kTranscriptMessagesTabId;

  // Helper function to update both store and URL
  const handleTabChange = (tabId: string) => {
    setSelectedTranscriptTab(tabId);
    setSearchParams({ tab: tabId });
  };

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
      scrollable={true}
    >
      <ChatViewVirtualList
        id={"transcript-id"}
        messages={transcript.messages || []}
        toolCallStyle={"complete"}
        indented={false}
        className={styles.chatList}
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
        scrollable={true}
      >
        <TranscriptView
          id={"transcript-events-list"}
          events={transcript.events || []}
          className={styles.eventsList}
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
        scrollable={true}
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
    <div className={clsx(styles.tabContainer)}>
      <TabSet
        id={"transcript-body"}
        type="pills"
        tabPanelsClassName={clsx(styles.tabSet)}
        tabControlsClassName={clsx(styles.tabControl)}
        className={clsx(styles.tabs)}
        tools={[]}
      >
        {tabPanels}
      </TabSet>
    </div>
  );
};
