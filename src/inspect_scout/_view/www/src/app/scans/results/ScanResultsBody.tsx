import { AllCommunityModule, ModuleRegistry } from "ag-grid-community";
import { ColumnTable } from "arquero";
import clsx from "clsx";
import { FC, useMemo } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";

import { DataframeView } from "../../../components/DataframeView";
import { ErrorPanel } from "../../../components/ErrorPanel";
import { NoContentsPanel } from "../../../components/NoContentsPanel";
import {
  getRelativePathFromParams,
  parseScanResultPath,
  scanResultRoute,
} from "../../../router/url";
import { useStore } from "../../../state/store";
import { Status } from "../../../types";
import { kSegmentDataframe, kSegmentList } from "../ScansPanelBody";

import { ScanResultsList } from "./list/ScanResultsList";
import styles from "./ScanResultsBody.module.css";
import { defaultColumns } from "./types";

const columnOrder = ["transcript_id", "value", "explanation", "metadata"];

// Register AG Grid modules
ModuleRegistry.registerModules([AllCommunityModule]);

export const ScanResultsBody: FC<{
  selectedScan: Status;
  selectedScanner: {
    name: string | undefined;
    columnTable: ColumnTable | undefined;
    isLoading: boolean;
    error: string | undefined;
  };
}> = ({
  selectedScan,
  selectedScanner: {
    columnTable,
    error,
    isLoading: isLoadingData,
    name: selectedScanner,
  },
}) => {
  const selectedResultsView =
    useStore((state) => state.selectedResultsView) || kSegmentList;

  const hasScanner = (columnTable?.numRows() || 0) > 0;
  const dataframeWrapText = useStore((state) => state.dataframeWrapText);
  const setVisibleScannerResultsCount = useStore(
    (state) => state.setVisibleScannerResultsCount
  );

  // Navigation setup
  const navigate = useNavigate();
  const params = useParams<{ "*": string }>();
  const [searchParams] = useSearchParams();
  const relativePath = getRelativePathFromParams(params);
  const { scanPath } = parseScanResultPath(relativePath);

  const dataframeFilterColumns = useStore(
    (state) => state.dataframeFilterColumns
  );

  const sortedColumns = useMemo(() => {
    const cols = dataframeFilterColumns || defaultColumns;
    return [...cols].sort(sortColumns);
  }, [dataframeFilterColumns]);

  return (
    <div className={clsx(styles.scrollContainer)}>
      {hasScanner && (
        <div style={{ height: "100%", width: "100%" }}>
          {selectedResultsView === kSegmentList && (
            <ScanResultsList
              columnTable={columnTable}
              id={`scan-list-${selectedScanner}`}
              selectedScan={selectedScan}
            />
          )}
          {selectedResultsView === kSegmentDataframe && (
            <DataframeView
              options={{ maxStrLen: 1024 }}
              columnTable={columnTable}
              sortedColumns={sortedColumns}
              showRowNumbers={true}
              wrapText={dataframeWrapText}
              onRowDoubleClicked={(row) => {
                // Navigate to the result detail view
                const uuid = (row as { uuid?: string }).uuid;
                if (uuid) {
                  const route = scanResultRoute(scanPath, uuid, searchParams);
                  void navigate(route);
                }
              }}
              onVisibleRowCountChanged={setVisibleScannerResultsCount}
            />
          )}
        </div>
      )}
      {!hasScanner && !isLoadingData && !error && (
        <NoContentsPanel text="No scanner data available." />
      )}
      {error && (
        <ErrorPanel
          title="Error Loading Dataframe"
          error={{ message: error }}
        />
      )}
    </div>
  );
};

const sortColumns = (a: string, b: string) => {
  const indexA = columnOrder.indexOf(a);
  const indexB = columnOrder.indexOf(b);
  if (indexA === -1 && indexB === -1) {
    // leave in natural order
    return 0;
  } else if (indexA === -1) {
    return 1;
  } else if (indexB === -1) {
    return -1;
  } else {
    return indexA - indexB;
  }
};
