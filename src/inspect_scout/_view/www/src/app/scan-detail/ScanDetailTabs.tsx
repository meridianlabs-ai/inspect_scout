import clsx from "clsx";
import { useSearchParams } from "react-router-dom";
import { useEffect } from "react";
import JSONPanel from "../../components/JsonPanel";
import { TabPanel, TabSet } from "../../components/TabSet";
import { useStore } from "../../state/store";

import styles from "./ScanDetailTabs.module.css";
import { ScanResults } from "./scan-results/ScanResults";
import { MetaDataGrid } from "../../content/MetaDataGrid";
import { ScanInfo } from "./scan-results/ScanInfo";

const kTabIdScans = "scan-detail-tabs-results";
const kTabIdInfo = "scan-detail-tabs-info";
const kTabIdScanners = "scan-detail-tabs-scanners";
const kTabIdJson = "scan-detail-tabs-json";

export const ScanDetailTabs: React.FC = () => {
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
      const validTabs = [kTabIdScans, kTabIdInfo, kTabIdScanners, kTabIdJson];
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

  return (
    <TabSet
      id={"scan-detail-tabs"}
      type="pills"
      tabPanelsClassName={clsx(styles.tabSet)}
      tabControlsClassName={clsx(styles.tabControl)}
      className={clsx(styles.tabs)}
    >
      <TabPanel
        id={kTabIdScans}
        selected={selectedTab === kTabIdScans || selectedTab === undefined}
        title="Results"
        onSelected={() => {
          handleTabChange(kTabIdScans);
        }}
      >
        <ScanResults />
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
        id={kTabIdScanners}
        selected={selectedTab === kTabIdScanners}
        title="Scanners"
        onSelected={() => {
          handleTabChange(kTabIdScanners);
        }}
      >
        Scanners
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
