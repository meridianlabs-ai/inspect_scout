import { skipToken } from "@tanstack/react-query";
import { VscodeSplitLayout } from "@vscode-elements/react-elements";
import { clsx } from "clsx";
import { FC, ReactNode, useCallback, useEffect, useMemo } from "react";
import { useSearchParams } from "react-router-dom";

import { ExtendedFindProvider } from "../../components/ExtendedFindProvider";
import { ApplicationIcons } from "../../components/icons";
import JSONPanel from "../../components/JsonPanel";
import { LoadingBar } from "../../components/LoadingBar";
import { TabPanel, TabSet } from "../../components/TabSet";
import { ToolButton } from "../../components/ToolButton";
import { EventNode, EventType } from "../../components/transcript/types";
import { useDocumentTitle } from "../../hooks/useDocumentTitle";
import {
  getScannerParam,
  getValidationParam,
  updateValidationParam,
} from "../../router/url";
import { useStore } from "../../state/store";
import { ScansNavbar } from "../components/ScansNavbar";
import { useScanRoute } from "../hooks/useScanRoute";
import { useSelectedScan } from "../hooks/useSelectedScan";
import { useSelectedScanResultData } from "../hooks/useSelectedScanResultData";
import { useSelectedScanResultInputData } from "../hooks/useSelectedScanResultInputData";
import { useAppConfig } from "../server/useAppConfig";
import { useHasTranscript } from "../server/useHasTranscript";
import { isTranscriptInput, ScanResultData } from "../types";
import { getScanDisplayName } from "../utils/scan";
import { getTranscriptDisplayName } from "../utils/transcript";
import { useScansDir } from "../utils/useScansDir";
import { useTranscriptsDir } from "../utils/useTranscriptsDir";
import { ValidationCaseEditor } from "../validation/components/ValidationCaseEditor";

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

  // Sync displayed result with URL - this ensures both selectedScanResult
  // (for list highlighting) and displayedScanResult (for route restoration)
  // stay in sync with what's actually being viewed
  const setSelectedScanResult = useStore(
    (state) => state.setSelectedScanResult
  );
  const setDisplayedScanResult = useStore(
    (state) => state.setDisplayedScanResult
  );
  useEffect(() => {
    if (scanResultUuid) {
      setSelectedScanResult(scanResultUuid);
      setDisplayedScanResult(scanResultUuid);
    }
  }, [scanResultUuid, setSelectedScanResult, setDisplayedScanResult]);

  const appConfig = useAppConfig();

  // Validation sidebar - URL is the source of truth
  const validationSidebarCollapsed = !getValidationParam(searchParams);

  const toggleValidationSidebar = useCallback(() => {
    setSearchParams((prevParams) => {
      const isCurrentlyOpen = getValidationParam(prevParams);
      return updateValidationParam(prevParams, !isCurrentlyOpen);
    });
  }, [setSearchParams]);

  const selectedTab = useStore((state) => state.selectedResultTab);
  const visibleScannerResults = useStore(
    (state) => state.visibleScannerResults
  );

  const setSelectedResultTab = useStore((state) => state.setSelectedResultTab);
  const { data: selectedResult, loading: resultLoading } =
    useSelectedScanResultData(scanResultUuid);

  const { loading: inputLoading, data: inputData } =
    useSelectedScanResultInputData(selectedResult?.uuid);

  // Set document title with task name and scan location
  const taskName =
    inputData && isTranscriptInput(inputData)
      ? getTranscriptDisplayName(inputData.input)
      : undefined;
  useDocumentTitle(
    taskName,
    getScanDisplayName(selectedScan, appConfig.scans.dir),
    "Scans"
  );

  const { resolvedTranscriptsDir } = useTranscriptsDir(false);
  const { loading: hasTranscriptLoading, data: hasTranscript } =
    useHasTranscript(
      !selectedResult
        ? skipToken
        : { id: selectedResult.transcriptId, location: resolvedTranscriptsDir }
    );

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

  // TODO: lint react-hooks/preserve-manual-memoization - the lint seems to be a bug in the rule that doesn't account for the ?
  // However, this useMemo feels like a premature optimization. I think it should go
  // eslint-disable-next-line react-hooks/preserve-manual-memoization
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
    const toolButtons: ReactNode[] = [];

    // Existing highlight refs button (keep as-is)
    if (
      selectedTab === kTabIdInput &&
      selectedResult?.inputType === "transcript" &&
      selectedResult?.messageReferences.length > 0
    ) {
      toolButtons.push(
        <ToolButton
          icon={ApplicationIcons.highlight}
          key="highlight-labeled"
          latched={!!highlightLabeled}
          onClick={toggleHighlightLabeled}
          label="Highlight Refs"
        />
      );
    }

    // Validation button - only show when transcriptId is available
    if (selectedResult?.transcriptId) {
      toolButtons.push(
        <ToolButton
          key="validation-sidebar-toggle"
          label="Validation"
          icon={ApplicationIcons.edit}
          onClick={toggleValidationSidebar}
          title={
            validationSidebarCollapsed
              ? "Show validation editor"
              : "Hide validation editor"
          }
          subtle={true}
        />
      );
    }

    return toolButtons;
  }, [
    highlightLabeled,
    toggleHighlightLabeled,
    selectedTab,
    selectedResult,
    toggleValidationSidebar,
    validationSidebarCollapsed,
  ]);

  const renderTabSet = (resultData: ScanResultData) => (
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
          selected={selectedTab === kTabIdError || selectedTab === undefined}
          title="Error"
          onSelected={() => {
            handleTabChange(kTabIdError);
          }}
        >
          <ErrorPanel
            error={resultData.scanError}
            traceback={resultData.scanErrorTraceback}
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
          {resultData && inputData && (
            <ResultPanel
              resultData={resultData}
              inputData={inputData}
              transcriptDir={resolvedTranscriptsDir}
              hasTranscript={!!hasTranscript}
            />
          )}
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
            resultData={resultData}
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
        <MetadataPanel resultData={resultData} />
      </TabPanel>
      <TabPanel
        id={kTabIdInfo}
        selected={selectedTab === kTabIdInfo}
        title="Info"
        onSelected={() => {
          handleTabChange(kTabIdInfo);
        }}
      >
        <InfoPanel resultData={resultData} />
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
          data={resultData}
          simple={true}
          className={styles.json}
        />
      </TabPanel>
    </TabSet>
  );

  return (
    <div className={clsx(styles.root)}>
      <ScansNavbar
        scansDir={displayScansDir}
        scansDirSource={resolvedScansDirSource}
        setScansDir={setScansDir}
      >
        {visibleScannerResults.length > 0 && <ScannerResultNav />}
      </ScansNavbar>
      <LoadingBar
        loading={
          scanLoading || resultLoading || inputLoading || hasTranscriptLoading
        }
      />
      <ScannerResultHeader
        inputData={inputData}
        scan={selectedScan}
        appConfig={appConfig}
      />

      {selectedResult && (
        <ExtendedFindProvider>
          <div
            className={clsx(
              styles.contentArea,
              !validationSidebarCollapsed && styles.withValidation
            )}
          >
            {validationSidebarCollapsed || !selectedResult.transcriptId ? (
              <div className={styles.tabSetWrapper}>
                {renderTabSet(selectedResult)}
              </div>
            ) : (
              <VscodeSplitLayout
                className={styles.splitLayout}
                fixedPane="end"
                initialHandlePosition="80%"
                minEnd="180px"
                minStart="200px"
              >
                <div slot="start" className={styles.splitStart}>
                  {renderTabSet(selectedResult)}
                </div>
                <div slot="end" className={styles.validationSidebar}>
                  <ValidationCaseEditor
                    transcriptId={selectedResult.transcriptId}
                  />
                </div>
              </VscodeSplitLayout>
            )}
          </div>
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
