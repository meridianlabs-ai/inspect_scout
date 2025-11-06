import clsx from "clsx";
import { ReactNode, useEffect } from "react";
import { useSearchParams } from "react-router-dom";

import JSONPanel from "../../components/JsonPanel";
import { SegmentedControl } from "../../components/SegmentedControl";
import { TabPanel, TabSet } from "../../components/TabSet";
import { useStore } from "../../state/store";
import { ApplicationIcons } from "../appearance/icons";

import { ScanInfo } from "./info/ScanInfo";
import { ScanResultsPanel } from "./results/ScanResultsPanel";
import styles from "./ScanPanelBody.module.css";

const kTabIdScans = "scan-detail-tabs-results";
const kTabIdInfo = "scan-detail-tabs-info";
const kTabIdJson = "scan-detail-tabs-json";

export const kSegmentList = "list";
export const kSegmentDataframe = "dataframe";

export const ScanPanelBody: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const selectedTab = useStore((state) => state.selectedResultsTab);
  const setSelectedResultsTab = useStore(
    (state) => state.setSelectedResultsTab
  );
  const selectedResults = useStore((state) => state.selectedResults);

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

  const tools: ReactNode[] = [];
  if (selectedTab === kTabIdScans || selectedTab === undefined) {
    tools.push(
      <SegmentedControl
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
          data={selectedResults}
          simple={true}
        />
      </TabPanel>
    </TabSet>
  );
};
