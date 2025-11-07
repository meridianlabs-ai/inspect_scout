import { clsx } from "clsx";
import { FC, useEffect } from "react";
import { useParams, useSearchParams } from "react-router-dom";

import { ActivityBar } from "../../components/ActivityBar";
import { ExtendedFindProvider } from "../../components/ExtendedFindProvider";
import JSONPanel from "../../components/JsonPanel";
import { TabPanel, TabSet } from "../../components/TabSet";
import {
  getRelativePathFromParams,
  parseScanResultPath,
} from "../../router/url";
import { useStore } from "../../state/store";
import {
  useServerScans,
  useServerScanner,
  useSelectedResultsRow,
} from "../hooks";
import { Navbar } from "../navbar/Navbar";

import { InfoPanel } from "./info/InfoPanel";
import { InputPanel } from "./input/InputPanel";
import { ResultPanel } from "./result/ResultPanel";
import styles from "./ScanResultPanel.module.css";
import { TranscriptPanel } from "./transcript/TranscriptPanel";

const kTabIdResult = "Result";
const kTabIdInput = "Input";
const kTabIdInfo = "Info";
const kTabIdJson = "JSON";
const kTabIdTranscript = "transcript";

export const ScanResultPanel: FC = () => {
  useServerScans();
  useServerScanner();

  const params = useParams<{ "*": string }>();
  const relativePath = getRelativePathFromParams(params);
  const { scanResultUuid } = parseScanResultPath(relativePath);

  const loading = useStore((state) => state.loading);

  const [searchParams, setSearchParams] = useSearchParams();
  const selectedTab = useStore((state) => state.selectedResultTab);
  const setSelectedResultTab = useStore((state) => state.setSelectedResultTab);
  const selectedResult = useSelectedResultsRow(scanResultUuid);

  // Sync URL tab parameter with store on mount and URL changes
  useEffect(() => {
    const tabParam = searchParams.get("tab");
    if (tabParam) {
      // Valid tab IDs
      const validTabs = [
        kTabIdResult,
        kTabIdInput,
        kTabIdInfo,
        kTabIdJson,
        kTabIdTranscript,
      ];
      if (validTabs.includes(tabParam)) {
        setSelectedResultTab(tabParam);
      }
    }
  }, [searchParams, setSelectedResultTab]);

  // Helper function to update both store and URL
  const handleTabChange = (tabId: string) => {
    setSelectedResultTab(tabId);
    setSearchParams({ tab: tabId });
  };

  return (
    <div className={clsx(styles.root)}>
      <Navbar />
      <ActivityBar animating={!!loading} />
      <ExtendedFindProvider>
        <TabSet
          id={"scan-result-tabs"}
          type="pills"
          tabPanelsClassName={clsx(styles.tabSet)}
          tabControlsClassName={clsx(styles.tabControl)}
          className={clsx(styles.tabs)}
        >
          <TabPanel
            id={kTabIdResult}
            selected={selectedTab === kTabIdResult || selectedTab === undefined}
            title="Result"
            onSelected={() => {
              handleTabChange(kTabIdResult);
            }}
          >
            <ResultPanel result={selectedResult} />
          </TabPanel>
          <TabPanel
            id={kTabIdInput}
            selected={selectedTab === kTabIdInput}
            title="Input"
            onSelected={() => {
              handleTabChange(kTabIdInput);
            }}
          >
            <InputPanel />
          </TabPanel>
          <TabPanel
            id={kTabIdTranscript}
            selected={selectedTab === kTabIdTranscript}
            title="Transcript"
            onSelected={() => {
              handleTabChange(kTabIdTranscript);
            }}
          >
            <TranscriptPanel id="scan-transcript" result={selectedResult} />
          </TabPanel>
          <TabPanel
            id={kTabIdInfo}
            selected={selectedTab === kTabIdInfo}
            title="Info"
            onSelected={() => {
              handleTabChange(kTabIdInfo);
            }}
          >
            <InfoPanel scannerData={selectedResult} />
          </TabPanel>
          <TabPanel
            id={kTabIdJson}
            selected={selectedTab === kTabIdJson}
            title="JSON"
            onSelected={() => {
              handleTabChange(kTabIdJson);
            }}
          >
            <JSONPanel
              id="scan-result-json-contents"
              data={selectedResult}
              simple={true}
              className={styles.json}
            />
          </TabPanel>
        </TabSet>
      </ExtendedFindProvider>
    </div>
  );
};
