import { clsx } from "clsx";
import { FC, useCallback, useEffect, useMemo } from "react";
import { useSearchParams } from "react-router-dom";

import { ExtendedFindProvider } from "../../components/ExtendedFindProvider";
import { ApplicationIcons } from "../../components/icons";
import JSONPanel from "../../components/JsonPanel";
import { LoadingBar } from "../../components/LoadingBar";
import { TabPanel, TabSet } from "../../components/TabSet";
import { ToolButton } from "../../components/ToolButton";
import { EventNode, EventType } from "../../components/transcript/types";
import { getScannerParam } from "../../router/url";
import { useStore } from "../../state/store";
import { ScansNavbar } from "../components/ScansNavbar";
import { useScanRoute } from "../hooks/useScanRoute";
import { useSelectedScan } from "../hooks/useSelectedScan";
import { useSelectedScanResultData } from "../hooks/useSelectedScanResultData";
import { useSelectedScanResultInputData } from "../hooks/useSelectedScanResultInputData";
import { useScansDir } from "../utils/useScansDir";

import { ErrorPanel } from "./error/ErrorPanel";
import { InfoPanel } from "./info/InfoPanel";
import { MetadataPanel } from "./metadata/MetadataPanel";
import { ResultPanel } from "./result/ResultPanel";
import { ScannerResultHeader } from "./ScannerResultHeader";
import { ScannerResultNav } from "./ScannerResultNav";
import styles from "./ScannerResultPanel.module.css";
import { TranscriptPanel } from "./transcript/TranscriptPanel";

const kTabIdResult = "Result";
const kTabIdError = "Error";
const kTabIdInput = "Input";
const kTabIdInfo = "Info";
const kTabIdJson = "JSON";
const kTabIdTranscript = "transcript";
const kTabIdMetadata = "Metadata";

export const ScannerResultPanel: FC = () => {
  // Url data
  const { scanResultUuid } = useScanRoute();
  const [searchParams, setSearchParams] = useSearchParams();

  // Required server data
  const { loading: scanLoading, data: selectedScan } = useSelectedScan();
  const { displayScansDir, resolvedScansDirSource, setScansDir } =
    useScansDir(true);

  // Sync URL query param with store state
  const setSelectedScanner = useStore((state) => state.setSelectedScanner);
  useEffect(() => {
    const scannerParam = getScannerParam(searchParams);
    if (scannerParam) {
      setSelectedScanner(scannerParam);
    }
  }, [searchParams, setSelectedScanner]);

  const selectedTab = useStore((state) => state.selectedResultTab);
  const visibleScannerResults = useStore(
    (state) => state.visibleScannerResults
  );

  const setSelectedResultTab = useStore((state) => state.setSelectedResultTab);
  const { data: selectedResult, loading: resultLoading } =
    useSelectedScanResultData(scanResultUuid);

  const { loading: inputLoading, data: inputData } =
    useSelectedScanResultInputData();

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
    const newParams = new URLSearchParams(searchParams);
    newParams.set("tab", tabId);
    setSearchParams(newParams);
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

  const hasError =
    selectedResult?.scanError !== undefined &&
    selectedResult?.scanError !== null;

  const highlightLabeled = useStore((state) => state.highlightLabeled);
  const setHighlightLabeled = useStore((state) => state.setHighlightLabeled);
  const toggleHighlightLabeled = useCallback(() => {
    setHighlightLabeled(!highlightLabeled);
  }, [highlightLabeled, setHighlightLabeled]);

  const tools = useMemo(() => {
    if (
      selectedTab === kTabIdInput &&
      selectedResult?.inputType === "transcript" &&
      selectedResult?.messageReferences.length > 0
    ) {
      return [
        <ToolButton
          icon={ApplicationIcons.highlight}
          key="highlight-labeled"
          latched={!!highlightLabeled}
          onClick={toggleHighlightLabeled}
          label="Highlight Refs"
        />,
      ];
    } else {
      return [];
    }
  }, [highlightLabeled, toggleHighlightLabeled, selectedTab, selectedResult]);

  return (
    <div className={clsx(styles.root)}>
      <ScansNavbar
        scansDir={displayScansDir}
        scansDirSource={resolvedScansDirSource}
        setScansDir={setScansDir}
      >
        {visibleScannerResults.length > 0 && <ScannerResultNav />}
      </ScansNavbar>
      <LoadingBar loading={scanLoading || resultLoading || inputLoading} />
      <ScannerResultHeader inputData={inputData} scan={selectedScan} />

      {selectedResult && (
        <ExtendedFindProvider>
          <TabSet
            id={"scan-result-tabs"}
            type="pills"
            tabPanelsClassName={clsx(styles.tabSet)}
            tabControlsClassName={clsx(styles.tabControl)}
            className={clsx(styles.tabs)}
            tools={tools}
          >
            {hasError ? (
              <TabPanel
                id={kTabIdError}
                selected={
                  selectedTab === kTabIdError || selectedTab === undefined
                }
                title="Error"
                onSelected={() => {
                  handleTabChange(kTabIdError);
                }}
              >
                <ErrorPanel
                  error={selectedResult.scanError}
                  traceback={selectedResult.scanErrorTraceback}
                />
              </TabPanel>
            ) : undefined}
            {!hasError ? (
              <TabPanel
                id={kTabIdResult}
                selected={
                  selectedTab === kTabIdResult ||
                  (!hasError && selectedTab === undefined)
                }
                title="Result"
                scrollable={false}
                onSelected={() => {
                  handleTabChange(kTabIdResult);
                }}
                className={styles.fullHeight}
              >
                <ResultPanel
                  resultData={selectedResult}
                  inputData={inputData}
                />
              </TabPanel>
            ) : undefined}
            {showEvents ? (
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
                  resultData={selectedResult}
                  nodeFilter={skipScanSpan}
                />
              </TabPanel>
            ) : undefined}
            <TabPanel
              id={kTabIdMetadata}
              selected={selectedTab === kTabIdMetadata}
              title="Metadata"
              onSelected={() => {
                handleTabChange(kTabIdMetadata);
              }}
            >
              <MetadataPanel resultData={selectedResult} />
            </TabPanel>
            <TabPanel
              id={kTabIdInfo}
              selected={selectedTab === kTabIdInfo}
              title="Info"
              onSelected={() => {
                handleTabChange(kTabIdInfo);
              }}
            >
              <InfoPanel resultData={selectedResult} />
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
  if (nodes.length === 1 && nodes[0]?.event.event === "span_begin") {
    return nodes[0].children;
  }
  return nodes;
};
