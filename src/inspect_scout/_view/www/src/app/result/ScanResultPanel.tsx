import { clsx } from "clsx";
import { FC } from "react";
import { useParams } from "react-router-dom";

import { ActivityBar } from "../../components/ActivityBar";
import JSONPanel from "../../components/JsonPanel";
import { TabPanel, TabSet } from "../../components/TabSet";
import {
  getRelativePathFromParams,
  parseScanResultPath,
} from "../../router/url";
import { useStore } from "../../state/store";
import { useServerScans, useServerScanner } from "../hooks";
import { Navbar } from "../navbar/Navbar";

import { useSelectedResultsRow } from "./hooks";
import { InfoPanel } from "./info/InfoPanel";
import { InputPanel } from "./input/InputPanel";
import { ResultPanel } from "./result/ResultPanel";
import { ScanResultHeader } from "./ScanResultHeader";
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

  const singleFileMode = useStore((state) => state.singleFileMode);
  const loading = useStore((state) => state.loading);

  const selectedTab = useStore((state) => state.selectedResultTab);
  const setSelectedResultTab = useStore((state) => state.setSelectedResultTab);
  const scanData = useSelectedResultsRow(scanResultUuid);

  return (
    <div className={clsx(styles.root)}>
      {singleFileMode || <Navbar />}
      <ActivityBar animating={!!loading} />
      <ScanResultHeader />
      <TabSet
        id={"scan-result-tabs"}
        type="pills"
        tabPanelsClassName={clsx(styles.tabSet)}
        tabControlsClassName={clsx(styles.tabControl)}
        className={clsx(styles.tabs)}
        //tools={tools}
      >
        <TabPanel
          id={kTabIdResult}
          selected={selectedTab === kTabIdResult || selectedTab === undefined}
          title="Results"
          onSelected={() => {
            setSelectedResultTab(kTabIdResult);
          }}
        >
          <ResultPanel />
        </TabPanel>
        <TabPanel
          id={kTabIdInput}
          selected={selectedTab === kTabIdInput}
          title="Input"
          onSelected={() => {
            setSelectedResultTab(kTabIdInput);
          }}
        >
          <InputPanel />
        </TabPanel>
        <TabPanel
          id={kTabIdTranscript}
          selected={selectedTab === kTabIdTranscript}
          title="Transcript"
          onSelected={() => {
            setSelectedResultTab(kTabIdTranscript);
          }}
        >
          <TranscriptPanel />
        </TabPanel>
        <TabPanel
          id={kTabIdInfo}
          selected={selectedTab === kTabIdInfo}
          title="Info"
          onSelected={() => {
            setSelectedResultTab(kTabIdInfo);
          }}
        >
          <InfoPanel scannerData={scanData} />
        </TabPanel>
        <TabPanel
          id={kTabIdJson}
          selected={selectedTab === kTabIdJson}
          title="JSON"
          onSelected={() => {
            setSelectedResultTab(kTabIdJson);
          }}
        >
          <JSONPanel
            id="scan-result-json-contents"
            data={scanData}
            simple={true}
            className={styles.json}
          />
        </TabPanel>
      </TabSet>
    </div>
  );
};
