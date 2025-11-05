import type {
  ColDef,
  RowClickedEvent,
  StateUpdatedEvent,
} from "ag-grid-community";
import {
  AllCommunityModule,
  ModuleRegistry,
  themeBalham,
} from "ag-grid-community";
import { AgGridReact } from "ag-grid-react";
import { FC, useMemo } from "react";
import { useStore } from "../../state/store";

import styles from "./ScansGrid.module.css";
import { useNavigate, useParams } from "react-router-dom";
import { dirname, toRelativePath } from "../../utils/path";
import { getRelativePathFromParams } from "../../router/url";
import { ApplicationIcons } from "../appearance/icons";

// Register AG Grid modules
ModuleRegistry.registerModules([AllCommunityModule]);

const GRID_STATE_NAME = "ScansGrid";

interface ScanRow {
  status: "incomplete" | "complete" | "error";
  icon: string;
  model: string;
  timestamp: string;
  location: string;
  relativeLocation: string;
  scanId: string;
  scanName: string;
  scanners: string[];
}

export const ScansGrid: FC = () => {
  const params = useParams<{ "*": string }>();
  const paramsRelativePath = getRelativePathFromParams(params);

  const scans = useStore((state) => state.scans);
  const navigate = useNavigate();

  const gridStates = useStore((state) => state.gridStates);
  const setGridState = useStore((state) => state.setGridState);

  const resultsDir = useStore((state) => state.resultsDir);

  const gridState = useMemo(() => {
    const savedState = gridStates[GRID_STATE_NAME];
    // If no saved state, apply default sorting
    if (!savedState) {
      return {
        sort: {
          sortModel: [
            { colId: "icon", sort: "asc" as const },
            { colId: "timestamp", sort: "desc" as const },
          ],
        },
      };
    }
    return savedState;
  }, [gridStates]);

  // Transform logDetails into flat rows
  const data = useMemo(() => {
    const dirs = new Set<string>();
    const rows: ScanRow[] = [];

    scans.forEach((scan) => {
      const relativeLocation = toRelativePath(scan.location, resultsDir || "");

      const dir = dirname(relativeLocation);
      if (dir === paramsRelativePath) {
        const row: ScanRow = {
          icon:
            scan.errors.length > 1
              ? ApplicationIcons.error
              : scan.complete
                ? ApplicationIcons.success
                : ApplicationIcons.pendingTask,
          timestamp: scan.spec.timestamp,
          location: scan.location,
          relativeLocation: relativeLocation,
          scanId: scan.spec.scan_id,
          scanName: scan.spec.scan_name,
          model: scan.spec.model.model,
          status:
            scan.errors.length > 1
              ? "error"
              : scan.complete
                ? "complete"
                : "incomplete",
          scanners: Object.keys(scan.spec.scanners).map((s) => s),
        };
        rows.push(row);
      }

      if (!dirs.has(dir) && dir !== "" && dir !== paramsRelativePath) {
        dirs.add(dir);
        const dirRow: ScanRow = {
          timestamp: "",
          location: "",
          icon: ApplicationIcons.folder,
          relativeLocation: dir,
          scanId: "",
          scanName: dir,
          model: "",
          status: "incomplete",
          scanners: [],
        };
        rows.push(dirRow);
      }
    });

    return rows;
  }, [scans, resultsDir, paramsRelativePath]);

  // Create column definitions
  const columnDefs = useMemo((): ColDef<ScanRow>[] => {
    const baseColumns: ColDef<ScanRow>[] = [
      {
        field: "icon",
        headerName: "",
        initialWidth: 60,
        minWidth: 60,
        maxWidth: 60,
        sortable: true,
        filter: true,
        resizable: true,
        cellRenderer: (params: { value: string }) => {
          return <i className={params.value}></i>;
        },
      },
      {
        field: "scanName",
        headerName: "Name",
        initialWidth: 120,
        minWidth: 80,
        sortable: true,
        filter: true,
        resizable: true,
      },
      {
        field: "scanId",
        headerName: "Scan Id",
        initialWidth: 150,
        minWidth: 100,
        sortable: true,
        filter: true,
        resizable: true,
      },
      {
        field: "model",
        headerName: "Model",
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
        sortable: false,
        filter: false,
        resizable: true,
        valueFormatter: (params: { value: unknown[] }) =>
          params.value.join(", "),
      },
      {
        field: "timestamp",
        headerName: "Time",
        initialWidth: 150,
        minWidth: 100,
        sortable: true,
        filter: true,
        resizable: true,
      },
    ];

    return baseColumns;
  }, []);

  return (
    <div className={styles.gridWrapper}>
      <AgGridReact<ScanRow>
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
        onRowClicked={(e: RowClickedEvent<ScanRow>) => {
          if (e.data) {
            void navigate(`/scan/${e.data.relativeLocation}`);
          }
        }}
      />
    </div>
  );
};
