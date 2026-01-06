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

import { getRelativePathFromParams, scanRoute } from "../../router/url";
import { useStore } from "../../state/store";
import type { Status } from "../../types/api-types";
import { toRelativePath } from "../../utils/path";
import { debounce } from "../../utils/sync";
import { ApplicationIcons } from "../appearance/icons";

import styles from "./ScanJobsGrid.module.css";

// Register AG Grid modules
ModuleRegistry.registerModules([AllCommunityModule]);

const GRID_STATE_NAME = "ScanJobsGrid";

interface ScanJobSummary {
  status?: "incomplete" | "complete" | "error";
  type: "file" | "directory";
  model?: string;
  timestamp?: string;
  location?: string;
  relativeLocation: string;
  scanId?: string;
  name: string;
  scanners?: string[];
  errors?: boolean;
}

export const ScanJobGrid: FC<{
  scans: Status[];
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
          sortModel: [
            { colId: "type", sort: "asc" as const },
            { colId: "timestamp", sort: "desc" as const },
          ],
        },
      };
    }
    return savedState;
  }, [gridStates]);

  // Transform logDetails into flat rows
  const data = useMemo(() => {
    const rows: ScanJobSummary[] = [];

    scans.forEach((scan) => {
      const relativeLocation = toRelativePath(scan.location, resultsDir);

      const row: ScanJobSummary = {
        type: "file",
        timestamp: scan.spec.timestamp ?? "",
        location: scan.location,
        relativeLocation: relativeLocation,
        scanId: scan.spec.scan_id ?? "",
        name: scan.spec.scan_name ?? "",
        model: scan.spec.model?.model ?? "unknown",
        status:
          scan.errors.length > 1
            ? "error"
            : scan.complete
              ? "complete"
              : "incomplete",
        scanners: Object.keys(scan.spec.scanners).map((s) => s),
        errors: scan.errors.length > 0,
      };
      rows.push(row);
    });

    return rows;
  }, [scans, resultsDir, paramsRelativePath]);

  useEffect(() => {
    setVisibleScanJobCount(data.length);
  }, [data.length, setVisibleScanJobCount]);

  // Create column definitions
  const columnDefs = useMemo((): ColDef<ScanJobSummary>[] => {
    const baseColumns: ColDef<ScanJobSummary>[] = [
      {
        field: "status",
        headerName: "",
        initialWidth: 60,
        minWidth: 60,
        maxWidth: 60,
        sortable: true,
        filter: true,
        resizable: true,
        cellRenderer: (params: {
          value: string;
          data: Record<string, unknown>;
        }) => {
          if (params.data.type === "directory") {
            return (
              <i
                className={clsx(
                  ApplicationIcons["folder-fill"],
                  classNameForColor("blue")
                )}
              ></i>
            );
          } else {
            const icon =
              params.data.status === "complete"
                ? ApplicationIcons.success
                : params.data.errors
                  ? ApplicationIcons.error
                  : ApplicationIcons.pendingTask;
            const color =
              params.data.status === "complete"
                ? "green"
                : params.data.errors
                  ? "red"
                  : "yellow";

            return <i className={clsx(icon, classNameForColor(color))}></i>;
          }
        },
      },
      {
        field: "name",
        headerName: "Name",
        initialWidth: 120,
        minWidth: 80,
        sortable: true,
        filter: true,
        resizable: true,
      },
      {
        field: "scanners",
        headerName: "Scanners",
        initialWidth: 120,
        minWidth: 120,
        sortable: true,
        filter: true,
        resizable: true,
        valueGetter: (params) => {
          const scanners = params.data?.scanners;
          return Array.isArray(scanners) ? scanners.join(", ") : "-";
        },
      },

      {
        field: "scanId",
        headerName: "Scan Id",
        initialWidth: 150,
        minWidth: 100,
        sortable: true,
        filter: true,
        resizable: true,
        valueFormatter: (params) => {
          return params.data?.scanId ?? "-";
        },
      },
      {
        field: "model",
        headerName: "Model",
        initialWidth: 120,
        minWidth: 80,
        sortable: true,
        filter: true,
        resizable: true,
        valueFormatter: (params) => {
          return params.data?.model ?? "-";
        },
      },
      {
        field: "relativeLocation",
        headerName: "Path",
        initialWidth: 120,
        minWidth: 80,
        sortable: true,
        filter: true,
        resizable: true,
        valueFormatter: (params) => {
          return params.data?.relativeLocation ?? "-";
        },
      },
      {
        field: "timestamp",
        headerName: "Time",
        initialWidth: 150,
        minWidth: 100,
        sortable: true,
        filter: true,
        resizable: true,
        valueFormatter: (params) => {
          const timestamp = params.value;
          return timestamp ? new Date(timestamp).toLocaleString() : "-";
        },
        comparator: (valueA: string, valueB: string) => {
          // Handle empty timestamps (directories)
          if (!valueA) {
            return 1;
          }
          if (!valueB) {
            return -1;
          }

          return new Date(valueA).getTime() - new Date(valueB).getTime();
        },
      },
    ];

    return baseColumns;
  }, []);

  const gridRef = useRef<AgGridReact>(null);
  const resizeGridColumns = useCallback(
    debounce(() => {
      // Trigger column sizing after grid is ready
      gridRef.current?.api?.sizeColumnsToFit();
    }, 10),
    []
  );

  const onFilterChanged = useCallback(
    (event: FilterChangedEvent<ScanJobSummary>) => {
      const displayedRowCount = event.api.getDisplayedRowCount();
      setVisibleScanJobCount(displayedRowCount);
    },
    [setVisibleScanJobCount]
  );

  return (
    <div className={styles.gridWrapper}>
      <AgGridReact<ScanJobSummary>
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
        onStateUpdated={(e: StateUpdatedEvent<ScanJobSummary>) => {
          setGridState(GRID_STATE_NAME, e.state);
        }}
        rowClass={styles.row}
        onRowClicked={(e: RowClickedEvent<ScanJobSummary>) => {
          if (e.data) {
            if (!resultsDir) {
              return;
            }
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
