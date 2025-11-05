import { FC, useMemo } from "react";

import { AgGridReact } from "ag-grid-react";

import {
  AllCommunityModule,
  ModuleRegistry,
  themeBalham,
  type ColDef,
  type StateUpdatedEvent,
} from "ag-grid-community";
import { useStore } from "../../../state/store";
import { ColumnTable } from "arquero";

import styles from "./DataframeView.module.css";

// Register AG Grid modules
ModuleRegistry.registerModules([AllCommunityModule]);

// Grid state holder
const GRID_STATE_NAME = "DataframeView";

interface DataframeViewProps {
  columnTable: ColumnTable;
}

export const DataframeView: FC<DataframeViewProps> = ({ columnTable }) => {
  const gridStates = useStore((state) => state.gridStates);
  const setGridState = useStore((state) => state.setGridState);
  const gridState = useMemo(() => {
    const savedState = gridStates[GRID_STATE_NAME];
    // If no saved state, return undefined to use default grid state
    return savedState;
  }, [gridStates]);

  const { columnDefs, rowData } = useMemo(() => {
    // Create column definitions for ag-grid
    const columnDefs: ColDef[] = columnTable.columnNames().map((name) => {
      return {
        field: name,
        headerName: name,
        sortable: true,
        filter: true,
        resizable: true,
        wrapText: true,
        tooltipField: name,
      };
    });

    // Convert table to array of objects for ag-grid
    const rowData = columnTable.objects();

    return { columnDefs, rowData };
  }, [columnTable]);

  return (
    <div className={styles.gridWrapper}>
      <AgGridReact
        rowData={rowData}
        columnDefs={columnDefs}
        defaultColDef={{
          sortable: true,
          filter: true,
          resizable: true,
        }}
        rowHeight={100}
        animateRows={false}
        suppressColumnMoveAnimation={true}
        suppressCellFocus={true}
        theme={themeBalham}
        enableCellTextSelection={true}
        autoSizeStrategy={{ type: "fitGridWidth" }}
        initialState={gridState}
        onStateUpdated={(e: StateUpdatedEvent) => {
          setGridState(GRID_STATE_NAME, e.state);
        }}
      />
    </div>
  );
};
