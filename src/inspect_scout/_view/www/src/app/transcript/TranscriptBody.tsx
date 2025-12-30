import clsx from "clsx";
import { FC } from "react";
import { useSearchParams } from "react-router-dom";

import { ChatViewVirtualList } from "../../chat/ChatViewVirtualList";
import { TabPanel, TabSet } from "../../components/TabSet";
import { useStore } from "../../state/store";
import { Transcript } from "../../types/api-types";

import styles from "./TranscriptBody.module.css";

const kTranscriptMessagesTabId = "transcript-messages";

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

  // Helper function to update both store and URL
  const handleTabChange = (tabId: string) => {
    setSelectedTranscriptTab(tabId);
    setSearchParams({ tab: tabId });
  };
  return (
    <div>
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
          className={clsx("sample-tab", styles.fullWidth, styles.chat)}
          title="Messages"
          onSelected={() => {
            handleTabChange(kTranscriptMessagesTabId);
          }}
          selected={selectedTranscriptTab === kTranscriptMessagesTabId}
          scrollable={false}
        >
          <div>CHAT LIST</div>
        </TabPanel>
      </TabSet>
    </div>
  );
};
