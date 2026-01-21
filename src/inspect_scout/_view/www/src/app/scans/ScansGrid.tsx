import type {
  ColDef,
  FilterChangedEvent,
  RowClickedEvent,
  StateUpdatedEvent,
} from "ag-grid-community";
import {
  AllCommunityModule,
  ModuleRegistry,
  themeBalham,
} from "ag-grid-community";
import { AgGridReact } from "ag-grid-react";
import { clsx } from "clsx";
import { FC, useCallback, useEffect, useMemo, useRef } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { ApplicationIcons } from "../../components/icons";
import { getRelativePathFromParams, scanRoute } from "../../router/url";
import { useStore } from "../../state/store";
import type { ScanStatusWithActiveInfo } from "../../types/api-types";
import { toRelativePath } from "../../utils/path";
import { debounce } from "../../utils/sync";

import styles from "./ScansGrid.module.css";

// Register AG Grid modules
ModuleRegistry.registerModules([AllCommunityModule]);

const GRID_STATE_NAME = "ScanJobsGrid";

// Extends API type with computed relativeLocation for grid display
type ScanRow = ScanStatusWithActiveInfo & { relativeLocation: string };

export const ScansGrid: FC<{
  scans: ScanStatusWithActiveInfo[];
  resultsDir: string | undefined;
}> = ({ scans, resultsDir }) => {
  const params = useParams<{ "*": string }>();
  const paramsRelativePath = getRelativePathFromParams(params);
  const navigate = useNavigate();

  const gridStates = useStore((state) => state.gridStates);
  const setGridState = useStore((state) => state.setGridState);

  const setVisibleScanJobCount = useStore(
    (state) => state.setVisibleScanJobCount
  );

  const gridState = useMemo(() => {
    const savedState = gridStates[GRID_STATE_NAME];
    // If no saved state, apply default sorting
    if (!savedState?.sort) {
      return {
        sort: {
          sortModel: [{ colId: "timestamp", sort: "desc" as const }],
        },
      };
    }
    return savedState;
  }, [gridStates]);

  // Add computed relativeLocation to each scan
  const data = useMemo(
    (): ScanRow[] =>
      scans.map((scan) => ({
        ...scan,
        relativeLocation: toRelativePath(scan.location, resultsDir),
      })),
    [scans, resultsDir, paramsRelativePath]
  );

  useEffect(() => {
    setVisibleScanJobCount(data.length);
  }, [data.length, setVisibleScanJobCount]);

  // Create column definitions
  const columnDefs = useMemo((): ColDef<ScanRow>[] => {
    const baseColumns: ColDef<ScanRow>[] = [
      {
        colId: "status",
        headerName: "✓",
        initialWidth: 70,
        minWidth: 70,
        maxWidth: 70,
        sortable: true,
        filter: true,
        resizable: true,
        valueGetter: (params) => {
          const scan = params.data;
          if (!scan) return "";
          if (scan.active_scan_info) return "active";
          if (scan.errors.length > 0) return "error";
          return scan.complete ? "complete" : "incomplete";
        },
        cellRenderer: (params: {
          value: string;
          data: ScanRow | undefined;
        }) => {
          const scan = params.data;
          if (!scan) return null;

          const activeScan = scan.active_scan_info;
          if (activeScan) {
            const pct =
              activeScan.total_scans > 0
                ? Math.round(
                    (activeScan.metrics.completed_scans /
                      activeScan.total_scans) *
                      100
                  )
                : 0;
            return (
              <span className={classNameForColor("blue")}>
                <i className={ApplicationIcons["play-circle"]}></i> {pct}%
              </span>
            );
          }

          const hasErrors = scan.errors.length > 0;
          const icon = scan.complete
            ? ApplicationIcons.success
            : hasErrors
              ? ApplicationIcons.error
              : ApplicationIcons.pendingTask;
          const color = scan.complete ? "green" : hasErrors ? "red" : "yellow";

          return <i className={clsx(icon, classNameForColor(color))}></i>;
        },
      },
      {
        colId: "name",
        headerName: "Name",
        initialWidth: 120,
        minWidth: 80,
        sortable: true,
        filter: true,
        resizable: true,
        valueGetter: (params) => params.data?.spec.scan_name ?? "-",
      },
      {
        colId: "scanners",
        headerName: "Scanners",
        initialWidth: 120,
        minWidth: 120,
        sortable: true,
        filter: true,
        resizable: true,
        valueGetter: (params) => {
          const scanners = params.data?.spec.scanners;
          return scanners ? Object.keys(scanners).join(", ") : "-";
        },
      },
      {
        colId: "scanId",
        headerName: "Scan Id",
        initialWidth: 150,
        minWidth: 100,
        sortable: true,
        filter: true,
        resizable: true,
        valueGetter: (params) => params.data?.spec.scan_id ?? "-",
      },
      {
        colId: "model",
        headerName: "Model",
        initialWidth: 120,
        minWidth: 80,
        sortable: true,
        filter: true,
        resizable: true,
        valueGetter: (params) => params.data?.spec.model?.model ?? "-",
      },
      {
        field: "relativeLocation",
        headerName: "Path",
        initialWidth: 120,
        minWidth: 80,
        sortable: true,
        filter: true,
        resizable: true,
      },
      {
        colId: "timestamp",
        headerName: "Time",
        initialWidth: 150,
        minWidth: 100,
        sortable: true,
        filter: true,
        resizable: true,
        valueGetter: (params) => params.data?.spec.timestamp ?? "",
        valueFormatter: (params) => {
          const timestamp = params.value;
          return timestamp ? new Date(timestamp).toLocaleString() : "-";
        },
        comparator: (valueA: string, valueB: string) => {
          if (!valueA) return 1;
          if (!valueB) return -1;
          return new Date(valueA).getTime() - new Date(valueB).getTime();
        },
      },
    ];

    return baseColumns;
  }, []);

  const gridRef = useRef<AgGridReact>(null);
  const resizeGridColumns = useCallback(
    debounce(() => {
      gridRef.current?.api?.sizeColumnsToFit();
    }, 10),
    []
  );

  const onFilterChanged = useCallback(
    (event: FilterChangedEvent<ScanRow>) => {
      const displayedRowCount = event.api.getDisplayedRowCount();
      setVisibleScanJobCount(displayedRowCount);
    },
    [setVisibleScanJobCount]
  );

  return (
    <div className={styles.gridWrapper}>
      <AgGridReact<ScanRow>
        ref={gridRef}
        rowData={data}
        columnDefs={columnDefs}
        defaultColDef={{
          sortable: true,
          filter: true,
          resizable: true,
        }}
        animateRows={false}
        suppressColumnMoveAnimation={true}
        suppressCellFocus={true}
        theme={themeBalham}
        enableCellTextSelection={true}
        autoSizeStrategy={{ type: "fitGridWidth" }}
        initialState={gridState}
        onStateUpdated={(e: StateUpdatedEvent<ScanRow>) => {
          setGridState(GRID_STATE_NAME, e.state);
        }}
        rowClass={styles.row}
        onRowClicked={(e: RowClickedEvent<ScanRow>) => {
          if (e.data && resultsDir) {
            void navigate(scanRoute(resultsDir, e.data.relativeLocation));
          }
        }}
        onGridSizeChanged={resizeGridColumns}
        onFilterChanged={onFilterChanged}
      />
    </div>
  );
};

const classNameForColor = (color: string): string | undefined => {
  switch (color) {
    case "green":
      return styles.green;
    case "yellow":
      return styles.yellow;
    case "red":
      return styles.red;
    case "blue":
      return styles.blue;
    default:
      return "";
  }
};
