import clsx from "clsx";
import { ReactNode, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { GRID_STATE_NAME } from "../../components/DataframeView";
import { ApplicationIcons } from "../../components/icons";
import JSONPanel from "../../components/JsonPanel";
import { SegmentedControl } from "../../components/SegmentedControl";
import { TabPanel, TabSet } from "../../components/TabSet";
import { useStore } from "../../state/store";
import { Status } from "../../types/api-types";
import { ResultGroup } from "../types";
import { resultIdentifierStr, resultLog } from "../utils/results";

import { ScanInfo } from "./info/ScanInfo";
import { DataframeGridApiProvider } from "./scanners/dataframe/DataframeGridApiContext";
import { ScannerDataframeClearFiltersButton } from "./scanners/dataframe/ScannerDataframeClearFiltersButton";
import { ScannerDataframeColumnsPopover } from "./scanners/dataframe/ScannerDataframeColumnsPopover";
import { ScannerDataframeCopyLinkButton } from "./scanners/dataframe/ScannerDataframeCopyLinkButton";
import {
  ScannerDataframeCopyCSVButton,
  ScannerDataframeDownloadCSVButton,
} from "./scanners/dataframe/ScannerDataframeCSVButtons";
import { ScannerDataframeFilterColumnsButton } from "./scanners/dataframe/ScannerDataframeFilterColumnsButton";
import { ScannerDataframeWrapTextButton } from "./scanners/dataframe/ScannerDataframeWrapTextButton";
import { ScannerResultsFilter } from "./scanners/results/ScannerResultsFilter";
import { ScannerResultsGroup } from "./scanners/results/ScannerResultsGroup";
import { ScannerResultsSearch } from "./scanners/results/ScannerResultsSearch";
import { ScannerPanel } from "./scanners/ScannerPanel";
import styles from "./ScanPanelBody.module.css";

const kTabIdScans = "scan-detail-tabs-results";
const kTabIdInfo = "scan-detail-tabs-info";
const kTabIdJson = "scan-detail-tabs-json";

export const kSegmentList = "list";
export const kSegmentDataframe = "dataframe";

export const ScanPanelBody: React.FC<{ selectedScan: Status }> = ({
  selectedScan,
}) => {
  const [searchParams, setSearchParams] = useSearchParams();
  const selectedTab = useStore((state) => state.selectedResultsTab);
  const setSelectedResultsTab = useStore(
    (state) => state.setSelectedResultsTab
  );

  const selectedScanner = useStore((state) => state.selectedScanner);
  const visibleScannerResults = useStore(
    (state) => state.visibleScannerResults
  );

  const chooseColumnnsRef = useRef<HTMLButtonElement | null>(null);
  const [buttonElement, setButtonElement] = useState<HTMLButtonElement | null>(
    null
  );

  const gridFilter = useStore(
    (state) => state.gridStates[GRID_STATE_NAME]?.filter
  );

  // Use a callback ref to capture the button element and trigger re-renders
  const buttonRefCallback = (element: HTMLButtonElement | null) => {
    chooseColumnnsRef.current = element;
    setButtonElement(element);
  };

  // Sync URL tab parameter with store on mount and URL changes
  useEffect(() => {
    const tabParam = searchParams.get("tab");
    if (tabParam) {
      // Valid tab IDs
      const validTabs = [kTabIdScans, kTabIdInfo, kTabIdJson];
      if (validTabs.includes(tabParam)) {
        setSelectedResultsTab(tabParam);
      }
    }
  }, [searchParams, setSelectedResultsTab]);

  // Helper function to update both store and URL
  const handleTabChange = (tabId: string) => {
    setSelectedResultsTab(tabId);
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        next.set("tab", tabId);
        return next;
      },
      { replace: true }
    );
  };

  const selectedResultsView =
    useStore((state) => state.selectedResultsView) || kSegmentList;
  const setSelectedResultsView = useStore(
    (state) => state.setSelectedResultsView
  );

  // Figure out whether grouping should be shown
  const groupOptions: Array<ResultGroup> = useMemo(() => {
    if (!visibleScannerResults || visibleScannerResults.length === 0) {
      return [];
    }

    const hasLabel = visibleScannerResults.some(
      (summary) => summary.label !== undefined && summary.label !== null
    );

    const logCount = visibleScannerResults.reduce((logs, summary) => {
      const log = resultLog(summary);
      if (log) {
        logs.add(log);
        return logs;
      } else {
        return logs;
      }
    }, new Set<string>()).size;
    const hasManyLogs = logCount > 1;

    const idStrs = visibleScannerResults
      .map((summary) => resultIdentifierStr(summary))
      .filter((id): id is string => id !== undefined);
    const hasRepeatedIds = idStrs.length !== new Set(idStrs).size;

    const epochStrs = visibleScannerResults
      .map((summary) => summary.transcriptMetadata.epoch)
      .filter((e): e is number => e !== undefined);
    const hasEpochs = new Set(epochStrs).size > 1;

    const models = visibleScannerResults
      .map((summary) => summary.transcriptModel)
      .filter((m) => m !== undefined);
    const hasModels = models.length > 1;

    const options: Array<ResultGroup> = [];
    if (hasLabel) {
      options.push("label");
    }
    if (hasManyLogs) {
      options.push("source");
    }
    if (hasRepeatedIds) {
      options.push("id");
    }
    if (hasEpochs) {
      options.push("epoch");
    }
    if (hasModels) {
      options.push("model");
    }
    return options;
    // TODO: lint react-hooks/exhaustive-deps - refactor to avoid the lint
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedScanner, visibleScannerResults]);

  const tools: ReactNode[] = [];
  if (selectedTab === kTabIdScans || selectedTab === undefined) {
    if (selectedResultsView === kSegmentList) {
      tools.push(<ScannerResultsSearch key={"scan-results-search"} />);
    }

    if (selectedResultsView === kSegmentList) {
      tools.push(<ScannerResultsFilter key={"scan-results-filtering"} />);
    }

    if (selectedResultsView === kSegmentDataframe) {
      tools.push(
        <ScannerDataframeCopyCSVButton key="scan-dataframe-copy-csv" />
      );
      tools.push(
        <ScannerDataframeDownloadCSVButton key="scan-dataframe-download-csv" />
      );
      tools.push(
        <ScannerDataframeCopyLinkButton key="scan-dataframe-copy-link" />
      );
      tools.push(
        <ScannerDataframeWrapTextButton key="scan-dataframe-wrap-text" />
      );
    }

    if (selectedResultsView === kSegmentDataframe) {
      tools.push(
        <ScannerDataframeFilterColumnsButton
          key="scan-dataframe-filter-columns"
          ref={buttonRefCallback}
        />
      );
    }

    if (selectedResultsView === kSegmentDataframe && gridFilter) {
      tools.push(<ScannerDataframeClearFiltersButton />);
    }

    if (selectedResultsView === kSegmentList && groupOptions.length > 0) {
      tools.push(
        <ScannerResultsGroup
          key={"scan-results-grouping"}
          options={groupOptions}
        />
      );
    }

    tools.push(
      <SegmentedControl
        key={"scan-results-view-segmented-control"}
        selectedId={selectedResultsView}
        segments={[
          {
            id: kSegmentList,
            label: kSegmentList,
            icon: ApplicationIcons.file,
          },
          {
            icon: ApplicationIcons.samples,
            id: kSegmentDataframe,
            label: kSegmentDataframe,
          },
        ]}
        onSegmentChange={(segmentId: string, _index: number) => {
          setSelectedResultsView(segmentId);
        }}
      />
    );
  }

  return (
    <DataframeGridApiProvider>
      <TabSet
        id={"scan-detail-tabs"}
        type="pills"
        tabPanelsClassName={clsx(styles.tabSet)}
        tabControlsClassName={clsx(styles.tabControl)}
        className={clsx(styles.tabs)}
        tools={tools}
      >
        <TabPanel
          id={kTabIdScans}
          selected={selectedTab === kTabIdScans || selectedTab === undefined}
          title="Results"
          onSelected={() => {
            handleTabChange(kTabIdScans);
          }}
        >
          <ScannerPanel selectedScan={selectedScan} />
        </TabPanel>

        <TabPanel
          id={kTabIdInfo}
          selected={selectedTab === kTabIdInfo}
          title="Info"
          onSelected={() => {
            handleTabChange(kTabIdInfo);
          }}
        >
          <ScanInfo selectedScan={selectedScan} />
        </TabPanel>
        <TabPanel
          id={kTabIdJson}
          selected={selectedTab === kTabIdJson}
          title="JSON"
          onSelected={() => {
            handleTabChange(kTabIdJson);
          }}
          scrollable={true}
        >
          <JSONPanel
            id="task-json-contents"
            data={selectedScan}
            simple={true}
          />
        </TabPanel>
      </TabSet>
      {selectedResultsView === kSegmentDataframe && buttonElement && (
        <ScannerDataframeColumnsPopover positionEl={buttonElement} />
      )}
    </DataframeGridApiProvider>
  );
};
