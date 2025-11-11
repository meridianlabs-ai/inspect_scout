import { AllCommunityModule, ModuleRegistry } from "ag-grid-community";
import clsx from "clsx";
import { FC } from "react";

import { DataframeView } from "../../../components/DataframeView";
import { NoContentsPanel } from "../../../components/NoContentsPanel";
import { useStore } from "../../../state/store";
import { useSelectedScanner } from "../../hooks";
import { kSegmentDataframe, kSegmentList } from "../ScannerPanelBody";

import { ScanResultsList } from "./list/ScanResultsList";
import styles from "./ScanResultsBody.module.css";

// Register AG Grid modules
ModuleRegistry.registerModules([AllCommunityModule]);

export const ScanResultsBody: FC = () => {
  const selectedScanner = useSelectedScanner();
  const selectedResultsView =
    useStore((state) => state.selectedResultsView) || kSegmentList;
  const columnTable = useStore((state) => state.selectedScanResultData);

  const isLoadingData = useStore((state) => state.loadingData);
  const isLoading = useStore((state) => state.loading);
  const hasScanner = columnTable?.numRows() > 0;

  return (
    <div className={clsx(styles.scrollContainer)}>
      {hasScanner && (
        <div style={{ height: "100%", width: "100%" }}>
          {selectedResultsView === kSegmentList && (
            <ScanResultsList
              columnTable={columnTable}
              id={`scan-list-${selectedScanner}`}
            />
          )}
          {selectedResultsView === kSegmentDataframe && (
            <DataframeView columnTable={columnTable} />
          )}
        </div>
      )}
      {!hasScanner && !isLoadingData && !isLoading && (
        <NoContentsPanel text="No scanner data available." />
      )}
    </div>
  );
};
