import clsx from "clsx";
import { FC, useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { PopOver } from "../../../../components/PopOver";
import { getColumnsParam, updateColumnsParam } from "../../../../router/url";
import { useStore } from "../../../../state/store";
import { ColumnPreset, useUserSettings } from "../../../../state/userSettings";

import { defaultColumns } from "./../types";
import styles from "./ScannerDataframeColumnsPopover.module.css";

export interface ScannerDataframeColumnsPopoverProps {
  positionEl: HTMLElement | null;
}

const columnsGroups = {
  Transcript: [
    "transcript_id",
    "transcript_source_type",
    "transcript_source_id",
    "transcript_source_uri",
    "transcript_metadata",
    "transcript_date",
    "transcript_task_set",
    "transcript_task_id",
    "transcript_task_repeat",
    "transcript_agent",
    "transcript_agent_args",
    "transcript_model",
    "transcript_score",
    "transcript_success",
    "transcript_message_count",
    "transcript_total_time",
    "transcript_total_tokens",
    "transcript_error",
    "transcript_limit",
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
  Input: ["input_type", "input_ids"],
  Validation: ["validation_target", "validation_result"],
  Result: [
    "uuid",
    "value",
    "explanation",
    "metadata",
    "label",
    "value_type",
    "answer",
    "scan_total_tokens",
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

/**
 * Hook to sync dataframe column selection with the URL `cols` query param.
 * On mount, if `cols` is present in the URL, applies those columns.
 * On column changes, updates the URL param to keep it in sync.
 */
const useColumnsUrlSync = (filtered: string[], isDefault: boolean) => {
  const [searchParams, setSearchParams] = useSearchParams();
  const setFilteredColumns = useStore(
    (state) => state.setDataframeFilterColumns
  );
  const initializedRef = useRef(false);
  const skipFirstSyncRef = useRef(true);

  // On mount: apply URL columns if present
  useEffect(() => {
    if (initializedRef.current) return;
    initializedRef.current = true;

    const urlColumns = getColumnsParam(searchParams);
    if (urlColumns) {
      setFilteredColumns(urlColumns);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // On column changes: update URL param (skip first run to avoid overwriting
  // the URL before the store has re-rendered with the URL-sourced columns)
  useEffect(() => {
    if (skipFirstSyncRef.current) {
      skipFirstSyncRef.current = false;
      return;
    }

    setSearchParams(
      (prev) => updateColumnsParam(prev, isDefault ? undefined : filtered),
      { replace: true }
    );
  }, [filtered, isDefault, setSearchParams]);
};

const InlinePresets: FC<{ filtered: string[] }> = ({ filtered }) => {
  const presets = useUserSettings((s) => s.dataframeColumnPresets);
  const setPresets = useUserSettings((s) => s.setDataframeColumnPresets);
  const setFilteredColumns = useStore(
    (state) => state.setDataframeFilterColumns
  );
  const [isSaving, setIsSaving] = useState(false);
  const [presetName, setPresetName] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isSaving && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isSaving]);

  const handleSave = () => {
    const name = presetName.trim();
    if (!name) return;
    const newPreset: ColumnPreset = { name, columns: [...filtered] };
    setPresets([...presets, newPreset]);
    setPresetName("");
    setIsSaving(false);
  };

  const handleDelete = (index: number, e: React.MouseEvent) => {
    e.stopPropagation();
    setPresets(presets.filter((_, i) => i !== index));
  };

  const handleLoad = (preset: ColumnPreset) => {
    setFilteredColumns(preset.columns);
  };

  if (presets.length === 0 && !isSaving) {
    return (
      <>
        |
        <a className={styles.link} onClick={() => setIsSaving(true)}>
          Save current...
        </a>
      </>
    );
  }

  return (
    <>
      {presets.map((preset, index) => (
        <span key={index}>
          |
          <span className={styles.presetItem}>
            <a
              className={styles.link}
              onClick={() => handleLoad(preset)}
              title={`Load "${preset.name}" (${preset.columns.length} columns)`}
            >
              {preset.name}
            </a>
            <button
              className={styles.presetDelete}
              onClick={(e) => handleDelete(index, e)}
              title={`Delete "${preset.name}"`}
            >
              <i className="bi bi-x-circle" />
            </button>
          </span>
        </span>
      ))}
      |
      {isSaving ? (
        <span className={styles.presetSaveRow}>
          <input
            ref={inputRef}
            className={styles.presetInput}
            type="text"
            placeholder="Preset name"
            value={presetName}
            onChange={(e) => setPresetName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") handleSave();
              if (e.key === "Escape") {
                setIsSaving(false);
                setPresetName("");
              }
            }}
          />
          <a className={styles.link} onClick={handleSave}>
            Save
          </a>
          <a
            className={styles.link}
            onClick={() => {
              setIsSaving(false);
              setPresetName("");
            }}
          >
            Cancel
          </a>
        </span>
      ) : (
        <a className={styles.link} onClick={() => setIsSaving(true)}>
          Save current...
        </a>
      )}
    </>
  );
};

export const ScannerDataframeColumnsPopover: FC<
  ScannerDataframeColumnsPopoverProps
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

  useColumnsUrlSync(filtered, isDefaultFilter);

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
        <InlinePresets filtered={filtered} />
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
