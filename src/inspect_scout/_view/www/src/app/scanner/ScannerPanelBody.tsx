import clsx from "clsx";
import { ReactNode, useEffect, useMemo } from "react";
import { useSearchParams } from "react-router-dom";

import JSONPanel from "../../components/JsonPanel";
import { SegmentedControl } from "../../components/SegmentedControl";
import { TabPanel, TabSet } from "../../components/TabSet";
import { useStore } from "../../state/store";
import { ApplicationIcons } from "../appearance/icons";
import { resultIdentifierStr, resultLog } from "../utils/results";

import { ScanInfo } from "./info/ScanInfo";
import { ScanResultsFilter } from "./results/ScanResultsFilter";
import { ScanResultsGroup } from "./results/ScanResultsGroup";
import { ScanResultsPanel } from "./results/ScanResultsPanel";
import { ScanResultsSearch } from "./results/ScanResultsSearch";
import styles from "./ScannerPanelBody.module.css";

const kTabIdScans = "scan-detail-tabs-results";
const kTabIdInfo = "scan-detail-tabs-info";
const kTabIdJson = "scan-detail-tabs-json";

export const kSegmentList = "list";
export const kSegmentDataframe = "dataframe";

export const ScannerPanelBody: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const selectedTab = useStore((state) => state.selectedResultsTab);
  const setSelectedResultsTab = useStore(
    (state) => state.setSelectedResultsTab
  );
  const selectedStatus = useStore((state) => state.selectedScanStatus);

  const selectedScanner = useStore((state) => state.selectedScanner);
  const visibleScannerResults = useStore(
    (state) => state.visibleScannerResults
  );

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
    setSearchParams({ tab: tabId });
  };

  const selectedResultsView =
    useStore((state) => state.selectedResultsView) || kSegmentList;
  const setSelectedResultsView = useStore(
    (state) => state.setSelectedResultsView
  );

  // Figure out whether grouping should be shown
  const groupOptions: Array<"label" | "source" | "id" | "none"> =
    useMemo(() => {
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

      const options: Array<"label" | "source" | "id" | "none"> = [];
      if (hasLabel) {
        options.push("label");
      }
      if (hasManyLogs) {
        options.push("source");
      }
      if (hasRepeatedIds) {
        options.push("id");
      }
      return options;
    }, [selectedScanner, visibleScannerResults]);

  const tools: ReactNode[] = [];
  if (selectedTab === kTabIdScans || selectedTab === undefined) {
    if (selectedResultsView === kSegmentList) {
      tools.push(<ScanResultsSearch key={"scan-results-search"} />);
    }

    if (selectedResultsView === kSegmentList) {
      tools.push(<ScanResultsFilter key={"scan-results-filtering"} />);
    }

    if (selectedResultsView === kSegmentList && groupOptions.length > 0) {
      tools.push(
        <ScanResultsGroup
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
        <ScanResultsPanel />
      </TabPanel>

      <TabPanel
        id={kTabIdInfo}
        selected={selectedTab === kTabIdInfo}
        title="Info"
        onSelected={() => {
          handleTabChange(kTabIdInfo);
        }}
      >
        <ScanInfo />
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
          data={selectedStatus}
          simple={true}
        />
      </TabPanel>
    </TabSet>
  );
};
