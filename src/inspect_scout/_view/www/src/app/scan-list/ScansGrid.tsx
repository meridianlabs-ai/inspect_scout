import type {
  ColDef,
  RowClickedEvent,
  StateUpdatedEvent,
} from 'ag-grid-community';
import {
  AllCommunityModule,
  ModuleRegistry,
  themeBalham,
} from 'ag-grid-community';
import { AgGridReact } from 'ag-grid-react';
import { FC, useMemo } from 'react';
import { useStore } from '../../state/store';

import styles from './ScansGrid.module.css';
import { useNavigate } from 'react-router-dom';
import { toRelativePath } from '../../utils/path';

// Register AG Grid modules
ModuleRegistry.registerModules([AllCommunityModule]);

const GRID_STATE_NAME = "ScansGrid";

interface ScanRow {
  status: "incomplete" | "complete" | "error";
  model: string;
  timestamp: string;
  location: string;
  relativeLocation: string;
  scanId: string;
  scanName: string;
  scanners: string[];
}

export const ScansGrid: FC = () => {
  const scans = useStore((state) => state.scans);
  const navigate = useNavigate();

  const gridStates = useStore((state) => state.gridStates);
  const setGridState = useStore((state) => state.setGridState);

  const resultsDir = useStore((state) => state.resultsDir);

  const gridState = useMemo(() => {
    return gridStates[GRID_STATE_NAME] || {};
  }, [gridStates]);

  // Transform logDetails into flat rows
  const data = useMemo(() => {
    const rows: ScanRow[] = [];

    scans.forEach((scan) => {
      const relativeLocation = toRelativePath(scan.location, resultsDir || '');
      const row: ScanRow = {
        timestamp: scan.spec.timestamp,
        location: scan.location,
        relativeLocation: relativeLocation,
        scanId: scan.spec.scan_id,
        scanName: scan.spec.scan_name,
        model: scan.spec.model.model,
        status: scan.errors.length > 1 ? "error" : scan.complete ? "complete" : "incomplete",
        scanners: Object.keys(scan.spec.scanners).map((s) => s),
      };
      rows.push(row);
    });

    return rows;
  }, [scans, resultsDir]);

  // Create column definitions
  const columnDefs = useMemo((): ColDef<ScanRow>[] => {
    const baseColumns: ColDef<ScanRow>[] = [
      {
        field: 'status',
        headerName: '',
        initialWidth: 60,
        minWidth: 60,
        maxWidth: 60,
        sortable: true,
        filter: true,
        resizable: true,
        cellRenderer: (params: { value: any; }) => (params.value === "error" ? '❌' : params.value === "complete" ? '✅' : '⏳'),
      },
      {
        field: 'timestamp',
        headerName: 'Time',
        initialWidth: 150,
        minWidth: 100,
        sortable: true,
        filter: true,
        resizable: true,
      },
      {
        field: 'scanId',
        headerName: 'Scan Id',
        initialWidth: 150,
        minWidth: 100,
        sortable: true,
        filter: true,
        resizable: true,
      },
      {
        field: 'scanName',
        headerName: 'Name',
        initialWidth: 120,
        minWidth: 80,
        sortable: true,
        filter: true,
        resizable: true,
      },
      {
        field: 'model',
        headerName: 'Model',
        initialWidth: 120,
        minWidth: 80,
        sortable: true,
        filter: true,
        resizable: true,
      },
      {
        field: 'scanners',
        headerName: 'Scanners',
        initialWidth: 120,
        minWidth: 120,
        sortable: false,
        filter: false,
        resizable: true,
        valueFormatter: (params: { value: any[]; }) => params.value.join(', '),
      }
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
