import clsx from "clsx";
import { FC, useCallback } from "react";

import { PopOver } from "../../../components/PopOver";
import { useStore } from "../../../state/store";

import styles from "./ScanDataframeColumnsPopover.module.css";
import { defaultColumns } from "./types";

export interface ScanDataframeColumnsPopoverProps {
  positionEl: HTMLElement | null;
}

const columnsGroups = {
  Transcript: [
    "transcript_id",
    "transcript_source_type",
    "transcript_source_id",
    "transcript_source_uri",
    "transcript_metadata",
  ],
  Scan: [
    "scan_id",
    "scan_tags",
    "scan_metadata",
    "scan_git_origin",
    "scan_git_version",
    "scan_git_commit",
  ],
  Scanner: [
    "scanner_key",
    "scanner_name",
    "scanner_version",
    "scanner_package_version",
    "scanner_file",
    "scanner_params",
  ],
  Input: ["input_type", "input_ids", "input"],
  Validation: ["validation_target", "validation_result"],
  Result: [
    "uuid",
    "value",
    "explanation",
    "metadata",
    "label",
    "value_type",
    "answer",
    "scan_tokens_total",
    "scan_model_usage",
    "scan_events",
    "timestamp",
    "message_references",
    "event_references",
  ],
  Error: ["scan_error", "scan_error_traceback", "scan_error_type"],
};

const useDataframeColumns = () => {
  const allColumns: string[] = Object.values(columnsGroups).flat();

  const filteredColumns =
    useStore((state) => state.dataframeFilterColumns) || defaultColumns;
  const setFilteredColumns = useStore(
    (state) => state.setDataframeFilterColumns
  );
  const isDefaultFilter =
    filteredColumns?.length === defaultColumns.length &&
    filteredColumns.every((col) => defaultColumns.includes(col));
  const isAllFilter = filteredColumns?.length === allColumns.length;
  const setDefaultFilter = () => {
    setFilteredColumns(defaultColumns);
  };
  const setAllFilter = () => {
    setFilteredColumns(allColumns);
  };
  const filterColumn = useCallback(
    (column: string, show: boolean) => {
      if (show && !filteredColumns?.includes(column)) {
        setFilteredColumns([...(filteredColumns || []), column]);
      } else if (!show) {
        setFilteredColumns(filteredColumns?.filter((c) => c !== column) || []);
      }
    },
    [filteredColumns, setFilteredColumns]
  );

  const arrangedColumns = (cols: number): Record<string, string[]>[] => {
    // Returns an array of records, one for each column of checkboxes
    // Each record maps group names to arrays of columns in that group

    // Define the desired order of groups with "---" as column break separator
    const groupOrder = [
      "Result",
      "Input",
      "---",
      "Transcript",
      "Validation",
      "Error",
      "---",
      "Scan",
      "Scanner",
    ];

    // Group all available columns by their group
    const groupedColumns: Record<string, string[]> = {};

    Object.entries(columnsGroups).forEach(([groupName, columns]) => {
      const columnsInGroup = columns.filter((col) => {
        // Handle wildcard patterns like "validation_result_*"
        if (col.endsWith("*")) {
          const prefix = col.slice(0, -1);
          return allColumns.some((c) => c.startsWith(prefix));
        }
        return allColumns.includes(col);
      });

      if (columnsInGroup.length > 0) {
        groupedColumns[groupName] = columnsInGroup;
      }
    });

    // Split groupOrder by separator and distribute into columns
    const result: Record<string, string[]>[] = [];
    let currentColumn: Record<string, string[]> = {};

    groupOrder.forEach((item) => {
      if (item === "---") {
        // Start a new column
        if (Object.keys(currentColumn).length > 0) {
          result.push(currentColumn);
          currentColumn = {};
        }
      } else if (groupedColumns[item]) {
        // Add group to current column
        currentColumn[item] = groupedColumns[item];
      }
    });

    // Add the last column if it has content
    if (Object.keys(currentColumn).length > 0) {
      result.push(currentColumn);
    }

    // Pad with empty columns if needed to match requested column count
    while (result.length < cols) {
      result.push({});
    }

    return result;
  };

  return {
    defaultFilter: defaultColumns,
    isDefaultFilter,
    isAllFilter,
    setDefaultFilter,
    setAllFilter,
    filterColumn,
    filtered: filteredColumns || [],
    arrangedColumns,
  };
};

export const ScanDataframeColumnsPopover: FC<
  ScanDataframeColumnsPopoverProps
> = ({ positionEl }) => {
  const showFilter = useStore((state) => state.dataframeShowFilterColumns);
  const setShowFilter = useStore(
    (state) => state.setDataframeShowFilterColumns
  );

  const {
    isDefaultFilter,
    isAllFilter,
    setDefaultFilter,
    setAllFilter,
    filterColumn,
    filtered,
    arrangedColumns,
  } = useDataframeColumns();
  return (
    <PopOver
      id={`scandata-choose-columns-popover`}
      positionEl={positionEl}
      isOpen={!!showFilter}
      setIsOpen={setShowFilter}
      placement="bottom-end"
      hoverDelay={-1}
    >
      <div className={clsx(styles.links, "text-size-smaller")}>
        <a
          className={clsx(
            styles.link,
            isDefaultFilter ? styles.selected : undefined
          )}
          onClick={() => setDefaultFilter()}
        >
          Default
        </a>
        |
        <a
          className={clsx(
            styles.link,
            isAllFilter ? styles.selected : undefined
          )}
          onClick={() => setAllFilter()}
        >
          All
        </a>
      </div>

      <div className={clsx(styles.grid, "text-size-smaller")}>
        {arrangedColumns(3).map((columnGroup, colIndex) => {
          return (
            <div key={colIndex}>
              {Object.entries(columnGroup).map(([groupName, columns]) => (
                <div key={groupName}>
                  <div
                    style={{
                      fontWeight: 600,
                      marginTop: "0.5em",
                      marginBottom: "0.25em",
                    }}
                  >
                    {groupName}
                  </div>
                  {columns.map((column) => (
                    <div
                      key={column}
                      className={clsx(styles.row)}
                      onClick={() => {
                        filterColumn(column, !filtered.includes(column));
                      }}
                    >
                      <input
                        type="checkbox"
                        checked={filtered.includes(column)}
                        onChange={(e) => {
                          filterColumn(column, e.target.checked);
                        }}
                      ></input>
                      {column}
                    </div>
                  ))}
                </div>
              ))}
            </div>
          );
        })}
      </div>
    </PopOver>
  );
};
