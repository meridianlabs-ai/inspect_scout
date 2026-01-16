import {
  AllCommunityModule,
  FilterChangedEvent,
  FirstDataRenderedEvent,
  GridApi,
  GridReadyEvent,
  ModuleRegistry,
  themeBalham,
  type ColDef,
  type StateUpdatedEvent,
} from "ag-grid-community";
import { AgGridReact } from "ag-grid-react";
import { ColumnTable } from "arquero";
import { FC, useCallback, useEffect, useMemo, useRef } from "react";

import { useSetDataframeGridApi } from "../app/scan/scanners/dataframe/DataframeGridApiContext";
import { useStore } from "../state/store";
import { centerTruncate } from "../utils/format";

import styles from "./DataframeView.module.css";

// Register AG Grid modules
ModuleRegistry.registerModules([AllCommunityModule]);

// Grid state holder
export const GRID_STATE_NAME = "DataframeView";

interface DataframeViewProps {
  columnTable?: ColumnTable;
  sortedColumns?: string[];
  onRowDoubleClicked?: (rowData: object) => void;
  onVisibleRowCountChanged?: (count: number) => void;
  options?: {
    maxStrLen?: number;
  };
  enableKeyboardNavigation?: boolean;
  showRowNumbers?: boolean;
  wrapText?: boolean;
}

export const DataframeView: FC<DataframeViewProps> = ({
  columnTable,
  sortedColumns,
  onRowDoubleClicked,
  onVisibleRowCountChanged,
  options,
  enableKeyboardNavigation = true,
  showRowNumbers = false,
  wrapText = false,
}) => {
  const selectedDataframeRow =
    useStore((state) => state.selectedResultRow) || 0;
  const setSelectedDataframeRow = useStore(
    (state) => state.setSelectedResultRow
  );

  const setGridState = useStore((state) => state.setGridState);
  const gridState = useStore((state) => state.gridStates[GRID_STATE_NAME]);
  const setDataframeGridApi = useSetDataframeGridApi();

  const { columnDefs, rowData } = useMemo(() => {
    const columnNames = sortedColumns || columnTable?.columnNames() || [];

    // Create column definitions for ag-grid
    const dataColumnDefs: Array<ColDef> = columnTable
      ? columnNames
          .map((name) => {
            const col = columnTable.column(name);
            if (!col) {
              return undefined;
            }
            const sampleValue = col?.at(0);

            // Create value formatter based on truncation options and data type
            const valueFormatter = options
              ? (params: { value: unknown }) => {
                  if (params.value === null || params.value === undefined) {
                    return String(params.value);
                  }

                  // Handle strings with center truncation
                  if (typeof params.value === "string") {
                    return centerTruncate(params.value, options.maxStrLen);
                  }

                  return String(params.value);
                }
              : undefined;

            return {
              field: name,
              headerName: name,
              sortable: true,
              filter: true,
              resizable: true,
              tooltipField: name,
              maxWidth: 800,
              cellDataType:
                typeof sampleValue === "boolean" ? false : undefined,
              hide: !columnNames?.includes(name) || false,
              valueFormatter,
              wrapText: wrapText,
              autoHeight: wrapText,
            };
          })
          .filter((c) => c !== undefined)
      : [];

    // Add row numbers column if enabled (manual implementation for Community edition)
    const columnDefs: Array<ColDef> = showRowNumbers
      ? [
          {
            headerName: "",
            valueGetter: (params) => {
              return params.node?.rowIndex !== undefined &&
                params.node?.rowIndex !== null
                ? params.node.rowIndex + 1
                : "";
            },
            sortable: false,
            filter: false,
            resizable: false,
            width: 60,
            maxWidth: 60,
            minWidth: 60,
            pinned: "left",
            suppressMovable: true,
            cellClass: "row-number-cell",
            cellStyle: {
              textAlign: "right",
              paddingRight: "12px",
            },
            onCellClicked: (params) => {
              if (params.data && onRowDoubleClicked) {
                if (params.rowIndex !== null && params.rowIndex !== undefined) {
                  setSelectedDataframeRow(params.rowIndex);
                }
                onRowDoubleClicked(params.data);
              }
            },
          },
          ...dataColumnDefs,
        ]
      : dataColumnDefs;

    // Convert table to array of objects for ag-grid
    const rowData = columnTable?.objects();

    return { columnDefs, rowData };
  }, [
    columnTable,
    sortedColumns,
    options,
    showRowNumbers,
    wrapText,
    onRowDoubleClicked,
    setSelectedDataframeRow,
  ]);

  const gridRef = useRef<AgGridReact>(null);

  // Clear filters when filter state is removed
  useEffect(() => {
    if (gridRef.current?.api && gridState && !gridState.filter) {
      const currentFilterModel = gridRef.current.api.getFilterModel();
      if (currentFilterModel && Object.keys(currentFilterModel).length > 0) {
        gridRef.current.api.setFilterModel(null);
      }
    }
  }, [gridState]);

  // Select row when store changes
  useEffect(() => {
    if (gridRef.current?.api && selectedDataframeRow >= 0) {
      gridRef.current.api.forEachNode((node) => {
        node.setSelected(node.rowIndex === selectedDataframeRow);
      });
      // Ensure the selected row is visible
      gridRef.current.api.ensureIndexVisible(selectedDataframeRow);
    }
  }, [selectedDataframeRow]);

  // Navigation handlers
  const handleNext = useCallback(() => {
    const totalRows = rowData?.length ?? 0;
    if (selectedDataframeRow < totalRows - 1) {
      setSelectedDataframeRow(selectedDataframeRow + 1);
    }
  }, [selectedDataframeRow, rowData]);

  const handlePrevious = useCallback(() => {
    if (selectedDataframeRow > 0) {
      setSelectedDataframeRow(selectedDataframeRow - 1);
    }
  }, [selectedDataframeRow]);

  const handleEnter = useCallback(() => {
    if (
      gridRef.current?.api &&
      selectedDataframeRow >= 0 &&
      onRowDoubleClicked
    ) {
      const selectedNode =
        gridRef.current.api.getDisplayedRowAtIndex(selectedDataframeRow);
      if (selectedNode?.data) {
        onRowDoubleClicked(selectedNode.data);
      }
    }
  }, [selectedDataframeRow, onRowDoubleClicked]);

  // Global keyboard navigation
  useEffect(() => {
    if (!enableKeyboardNavigation) {
      return;
    }

    const handleGlobalKeyDown = (e: globalThis.KeyboardEvent) => {
      // Don't handle keyboard events if focus is on an input, textarea, or select element
      const activeElement = document.activeElement;
      const isInputFocused =
        activeElement &&
        (activeElement.tagName === "INPUT" ||
          activeElement.tagName === "TEXTAREA" ||
          activeElement.tagName === "SELECT");

      if (!isInputFocused) {
        const totalRows = rowData?.length ?? 0;

        if (e.key === "ArrowUp") {
          if (e.metaKey || e.ctrlKey) {
            // Cmd/Ctrl+ArrowUp: Go to first row
            if (totalRows > 0) {
              e.preventDefault();
              setSelectedDataframeRow(0);
            }
          } else if (selectedDataframeRow > 0) {
            e.preventDefault();
            handlePrevious();
          }
        } else if (e.key === "ArrowDown") {
          if (e.metaKey || e.ctrlKey) {
            // Cmd/Ctrl+ArrowDown: Go to last row
            if (totalRows > 0) {
              e.preventDefault();
              setSelectedDataframeRow(totalRows - 1);
            }
          } else if (selectedDataframeRow < totalRows - 1) {
            e.preventDefault();
            handleNext();
          }
        } else if (e.key === "Enter") {
          if (selectedDataframeRow >= 0) {
            e.preventDefault();
            handleEnter();
          }
        }
      }
    };

    // Use capture phase to catch event before it reaches other handlers
    document.addEventListener("keydown", handleGlobalKeyDown, true);

    return () => {
      document.removeEventListener("keydown", handleGlobalKeyDown, true);
    };
  }, [
    enableKeyboardNavigation,
    selectedDataframeRow,
    rowData,
    handleNext,
    handlePrevious,
    handleEnter,
  ]);

  const updateVisibleRowCount = useCallback(
    (api: GridApi) => {
      const displayedRowCount = api.getDisplayedRowCount();
      onVisibleRowCountChanged?.(displayedRowCount);
    },
    [onVisibleRowCountChanged]
  );

  // Store the grid API in the global store when ready
  const handleGridReady = useCallback(
    (e: GridReadyEvent) => {
      setDataframeGridApi(e.api);
    },
    [setDataframeGridApi]
  );

  // Clean up the grid API when unmounting
  useEffect(() => {
    return () => {
      setDataframeGridApi(null);
    };
  }, [setDataframeGridApi]);

  return (
    <div className={styles.gridWrapper}>
      <AgGridReact<object>
        ref={gridRef}
        rowData={rowData}
        columnDefs={columnDefs}
        defaultColDef={{
          sortable: true,
          filter: true,
          resizable: true,
        }}
        rowSelection={{
          mode: "singleRow",
          enableClickSelection: true,
          checkboxes: false,
        }}
        animateRows={false}
        suppressColumnMoveAnimation={true}
        suppressCellFocus={true}
        theme={themeBalham}
        enableCellTextSelection={true}
        initialState={gridState}
        onGridReady={handleGridReady}
        onFirstDataRendered={(e: FirstDataRenderedEvent) => {
          // Resize the columns
          e.api.sizeColumnsToFit();

          // update the visible row count
          updateVisibleRowCount(e.api);
        }}
        onStateUpdated={(e: StateUpdatedEvent) => {
          setGridState(GRID_STATE_NAME, e.state);
        }}
        onFilterChanged={(e: FilterChangedEvent) => {
          // update the visible row count
          updateVisibleRowCount(e.api);
        }}
        autoSizeStrategy={{
          type: "fitCellContents",
        }}
        onRowDoubleClicked={(e) => {
          if (e.data) {
            if (e.rowIndex !== null) {
              setSelectedDataframeRow(e.rowIndex);
            }
            onRowDoubleClicked?.(e.data);
          }
        }}
      />
    </div>
  );
};
