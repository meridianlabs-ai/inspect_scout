import { AllCommunityModule, ModuleRegistry } from "ag-grid-community";
import { fromArrow } from "arquero";
import clsx from "clsx";
import { FC, useMemo } from "react";

import { DataframeView } from "../../../components/DataframeView";
import { NoContentsPanel } from "../../../components/NoContentsPanel";
import { useStore } from "../../../state/store";
import { useSelectedResults, useSelectedScanner } from "../../hooks";
import { kSegmentDataframe, kSegmentList } from "../ScannerPanelBody";

import { ScanResultsList } from "./list/ScanResultsList";
import styles from "./ScanResultsBody.module.css";

// Register AG Grid modules
ModuleRegistry.registerModules([AllCommunityModule]);

export const ScanResultsBody: FC = () => {
  const selectedScanner = useSelectedScanner();
  const selectedResults = useSelectedResults();

  const selectedResultsView =
    useStore((state) => state.selectedResultsView) || kSegmentList;

  const columnTable = useMemo(() => {
    const scanner = selectedResults?.scanners[selectedScanner || ""];

    if (!scanner || !scanner.data) {
      return fromArrow(new ArrayBuffer(0));
    }

    // Decode base64 string to Uint8Array
    const binaryString = atob(scanner.data);
    const bytes = new Uint8Array(binaryString.length);
    for (let i = 0; i < binaryString.length; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }

    // Load Arrow data using Arquero
    const table = fromArrow(bytes.buffer);
    return table;
  }, [selectedScanner, selectedResults]);

  const hasScanner = columnTable.numRows() > 0;

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
      {!hasScanner && <NoContentsPanel text="No scanner data available." />}
    </div>
  );
};
