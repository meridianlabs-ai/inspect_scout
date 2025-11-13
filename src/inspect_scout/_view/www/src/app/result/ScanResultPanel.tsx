import { clsx } from "clsx";
import { FC, useEffect, useMemo } from "react";
import { useParams, useSearchParams } from "react-router-dom";

import { ActivityBar } from "../../components/ActivityBar";
import { ExtendedFindProvider } from "../../components/ExtendedFindProvider";
import JSONPanel from "../../components/JsonPanel";
import { TabPanel, TabSet } from "../../components/TabSet";
import {
  getRelativePathFromParams,
  getScannerParam,
  parseScanResultPath,
} from "../../router/url";
import { useStore } from "../../state/store";
import { EventNode, EventType } from "../../transcript/types";
import {
  useServerScans,
  useServerScanner,
  useServerScannerDataframe,
  useSelectedResultsRow,
} from "../hooks";
import { Navbar } from "../navbar/Navbar";

import { InfoPanel } from "./info/InfoPanel";
import { InputPanel } from "./input/InputPanel";
import { ResultPanel } from "./result/ResultPanel";
import { ScanResultHeader } from "./ScanResultHeader";
import { ScanResultNav } from "./ScanResultNav";
import styles from "./ScanResultPanel.module.css";
import { TranscriptPanel } from "./transcript/TranscriptPanel";

const kTabIdResult = "Result";
const kTabIdInput = "Input";
const kTabIdInfo = "Info";
const kTabIdJson = "JSON";
const kTabIdTranscript = "transcript";

export const ScanResultPanel: FC = () => {
  // Url data
  const params = useParams<{ "*": string }>();
  const relativePath = getRelativePathFromParams(params);
  const { scanResultUuid } = parseScanResultPath(relativePath);
  const [searchParams, setSearchParams] = useSearchParams();

  // Required server data
  useServerScans();
  useServerScanner();
  useServerScannerDataframe();

  // Sync URL query param with store state
  const setSelectedScanner = useStore((state) => state.setSelectedScanner);
  useEffect(() => {
    const scannerParam = getScannerParam(searchParams);
    if (scannerParam) {
      setSelectedScanner(scannerParam);
    }
  }, [searchParams, setSelectedScanner]);

  const loading = useStore((state) => state.loading);
  const selectedTab = useStore((state) => state.selectedResultTab);
  const visibleScannerResults = useStore(
    (state) => state.visibleScannerResults
  );

  const setSelectedResultTab = useStore((state) => state.setSelectedResultTab);
  const { data: selectedResult, isLoading: resultLoading } =
    useSelectedResultsRow(scanResultUuid);

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

  const handleTabChange = (tabId: string) => {
    setSelectedResultTab(tabId);
    setSearchParams({ tab: tabId });
  };

  const showEvents = useMemo(() => {
    if (!selectedResult?.scanEvents) {
      return false;
    }

    const hasNonSpanEvents = selectedResult.scanEvents.some((event) => {
      return event.event !== "span_begin" && event.event !== "span_end";
    });

    return hasNonSpanEvents;
  }, [selectedResult?.scanEvents]);

  return (
    <div className={clsx(styles.root)}>
      <Navbar>{visibleScannerResults.length > 0 && <ScanResultNav />}</Navbar>
      <ActivityBar animating={!!loading || resultLoading} />
      <ScanResultHeader result={selectedResult} />
      {selectedResult && (
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
              selected={
                selectedTab === kTabIdResult || selectedTab === undefined
              }
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
              <InputPanel result={selectedResult} />
            </TabPanel>
            {showEvents && (
              <TabPanel
                id={kTabIdTranscript}
                selected={selectedTab === kTabIdTranscript}
                title="Events"
                onSelected={() => {
                  handleTabChange(kTabIdTranscript);
                }}
              >
                <TranscriptPanel
                  id="scan-transcript"
                  result={selectedResult}
                  nodeFilter={skipScanSpan}
                />
              </TabPanel>
            )}
            <TabPanel
              id={kTabIdInfo}
              selected={selectedTab === kTabIdInfo}
              title="Info"
              onSelected={() => {
                handleTabChange(kTabIdInfo);
              }}
            >
              <InfoPanel result={selectedResult} />
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
      )}
    </div>
  );
};

const skipScanSpan = (
  nodes: EventNode<EventType>[]
): EventNode<EventType>[] => {
  if (nodes.length === 1 && nodes[0].event.event === "span_begin") {
    return nodes[0].children;
  }
  return nodes;
};
