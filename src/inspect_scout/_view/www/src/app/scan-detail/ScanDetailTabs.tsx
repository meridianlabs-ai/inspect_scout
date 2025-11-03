import clsx from "clsx";
import JSONPanel from "../../components/JsonPanel";
import { TabPanel, TabSet } from "../../components/TabSet";
import { useStore } from "../../state/store";

import styles from "./ScanDetailTabs.module.css";

const kTabIdScans = "scan-detail-tabs-results";
const kTabIdInfo = "scan-detail-tabs-info";
const kTabIdScanners = "scan-detail-tabs-scanners";
const kTabIdJson = "scan-detail-tabs-json";

export const ScanDetailTabs: React.FC = () => {
  const selectedTab = useStore((state) => state.selectedResultsTab);
  const setSelectedResultsTab = useStore(
    (state) => state.setSelectedResultsTab
  );
  const selectedResults = useStore((state) => state.selectedResults);

  return (
    <TabSet
      id={"scan-detail-tabs"}
      type="pills"
      tabPanelsClassName={clsx(styles.tabSet)}
      tabControlsClassName={clsx(styles.tabControl)}
      className={clsx(styles.tabs)}
    >
      <TabPanel
        id={kTabIdJson}
        selected={selectedTab === kTabIdJson || selectedTab === undefined}
        title="JSON"
        onSelected={() => {
          setSelectedResultsTab(kTabIdJson);
        }}
        scrollable={true}
      >
        <JSONPanel
          id="task-json-contents"
          data={selectedResults}
          simple={true}
        />
      </TabPanel>
      
      <TabPanel
        id={kTabIdScans}
        selected={selectedTab === kTabIdScans}
        title="Results"
        onSelected={() => {
          setSelectedResultsTab(kTabIdScans);
        }}
      >
        Results
      </TabPanel>
      <TabPanel
        id={kTabIdInfo}
        selected={selectedTab === kTabIdInfo}
        title="Info"
        onSelected={() => {
          setSelectedResultsTab(kTabIdInfo);
        }}
      >
        Info
      </TabPanel>
      <TabPanel
        id={kTabIdScanners}
        selected={selectedTab === kTabIdScanners}
        title="Scanners"
        onSelected={() => {
          setSelectedResultsTab(kTabIdScanners);
        }}
      >
        Scanners
      </TabPanel>
      
    </TabSet>
  );

  return <div>Scan Detail Tabs</div>;
};
