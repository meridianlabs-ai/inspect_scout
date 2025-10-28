import type {
  ColDef,
  RowClickedEvent,
  RowSelectedEvent,
  StateUpdatedEvent,
} from 'ag-grid-community';
import {
  AllCommunityModule,
  ModuleRegistry,
  themeBalham,
} from 'ag-grid-community';
import { AgGridReact } from 'ag-grid-react';
import { FC, useCallback, useMemo } from 'react';
import { useStore } from '../../state/store';

import styles from './ScansGrid.module.css';
import { useNavigate } from 'react-router-dom';

// Register AG Grid modules
ModuleRegistry.registerModules([AllCommunityModule]);

const GRID_STATE_NAME = "ScansGrid";

interface ScanRow {
  timestamp: string;
  scanId: string;
  scanName: string;
  scanners: string[];
}

export const ScansGrid: FC = () => {
  //const gridState = useStore((state) => state.logs.samplesListState.gridState);
  //const setGridState = useStore((state) => state.logsActions.setGridState);

  const scans = useStore((state) => state.scans);
  const navigate = useNavigate();

  const gridStates = useStore((state) => state.gridStates);
  const setGridState = useStore((state) => state.setGridState);

  const gridState = useMemo(() => {
    return gridStates[GRID_STATE_NAME] || {};
  }, [gridStates]);

  // Transform logDetails into flat rows
  const data = useMemo(() => {
    const rows: ScanRow[] = [];

    scans.forEach((scan) => {
      console.log({ s: scan.spec });
      const row: ScanRow = {
        timestamp: scan.spec.timestamp,
        scanId: scan.spec.scan_id,
        scanName: scan.spec.scan_name,
        scanners: Object.keys(scan.spec.scanners).map((s) => s),
      };
      rows.push(row);
    });

    return rows;
  }, [scans]);

  // Create column definitions
  const columnDefs = useMemo((): ColDef<ScanRow>[] => {
    const baseColumns: ColDef<ScanRow>[] = [
      {
        field: 'timestamp',
        headerName: 'Time',
        width: 150,
        minWidth: 100,
        sortable: true,
        filter: true,
        resizable: true,
      },
      {
        field: 'scanId',
        headerName: 'Scan Id',
        width: 150,
        minWidth: 100,
        sortable: true,
        filter: true,
        resizable: true,
      },
      {
        field: 'scanName',
        headerName: 'Name',
        width: 120,
        minWidth: 80,
        sortable: true,
        filter: true,
        resizable: true,
      },
    ];

    return baseColumns;
  }, []);

  // Handle row selection
  const onRowSelected = useCallback((event: RowSelectedEvent<ScanRow>) => {
    if (event.node.isSelected() && event.data) {
      console.log(`Selected: ScanId="${event.data.scanId}ş`);
    }
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
        rowSelection="single"
        onRowSelected={onRowSelected}
        theme={themeBalham}
        enableCellTextSelection={true}
        autoSizeStrategy={{ type: 'fitCellContents' }}
        initialState={gridState}
        onStateUpdated={(e: StateUpdatedEvent<ScanRow>) => {
          setGridState(GRID_STATE_NAME, e.state);
        }}
        onRowClicked={(e: RowClickedEvent<ScanRow>) => {
          if (e.data) {
            void navigate(`/scan/${e.data.scanId}`);
          }
        }}
      />
    </div>
  );
};
