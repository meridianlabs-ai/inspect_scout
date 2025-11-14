import {
  AllCommunityModule,
  ModuleRegistry,
  themeBalham,
  type ColDef,
  type StateUpdatedEvent,
} from "ag-grid-community";
import { AgGridReact } from "ag-grid-react";
import { ColumnTable } from "arquero";
import { FC, useMemo, useRef } from "react";

import { useStore } from "../state/store";

import styles from "./DataframeView.module.css";

// Register AG Grid modules
ModuleRegistry.registerModules([AllCommunityModule]);

// Grid state holder
const GRID_STATE_NAME = "DataframeView";

interface DataframeViewProps {
  columnTable?: ColumnTable;
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
    const columnDefs: ColDef[] = columnTable
      ? columnTable.columnNames().map((name) => {
          const col = columnTable.column(name);
          const sampleValue = col?.at(0);

          return {
            field: name,
            headerName: name,
            sortable: true,
            filter: true,
            resizable: true,
            tooltipField: name,
            maxWidth: 400,
            cellDataType: typeof sampleValue === "boolean" ? false : undefined,
          };
        })
      : [];

    // Convert table to array of objects for ag-grid
    const rowData = columnTable?.objects();

    return { columnDefs, rowData };
  }, [columnTable]);

  const gridRef = useRef<AgGridReact>(null);
  return (
    <div className={styles.gridWrapper}>
      <AgGridReact
        ref={gridRef}
        rowData={rowData}
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
        initialState={gridState}
        onStateUpdated={(e: StateUpdatedEvent) => {
          setGridState(GRID_STATE_NAME, e.state);
        }}
        autoSizeStrategy={{
          type: "fitCellContents",
        }}
      />
    </div>
  );
};
