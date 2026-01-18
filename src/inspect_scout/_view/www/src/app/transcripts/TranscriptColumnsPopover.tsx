import clsx from "clsx";
import { FC, useCallback, useMemo } from "react";

import { PopOver } from "../../components/PopOver";
import { useStore } from "../../state/store";
import { TranscriptInfo } from "../../types/api-types";

import { COLUMN_LABELS, DEFAULT_COLUMN_ORDER } from "./columns";
import styles from "./TranscriptColumnsPopover.module.css";

export interface TranscriptColumnsPopoverProps {
  positionEl: HTMLElement | null;
  isOpen: boolean;
  setIsOpen: (open: boolean) => void;
}

const DEFAULT_VISIBLE_COLUMNS: Array<keyof TranscriptInfo> = [
  "success",
  "date",
  "task_set",
  "task_id",
  "task_repeat",
  "model",
  "score",
  "message_count",
  "total_time",
  "total_tokens",
];

const useTranscriptColumns = () => {
  const visibleColumns =
    useStore((state) => state.transcriptsTableState.visibleColumns) ??
    DEFAULT_VISIBLE_COLUMNS;
  const setTableState = useStore((state) => state.setTranscriptsTableState);

  const isDefaultFilter = useMemo(
    () =>
      visibleColumns.length === DEFAULT_VISIBLE_COLUMNS.length &&
      visibleColumns.every((col) => DEFAULT_VISIBLE_COLUMNS.includes(col)),
    [visibleColumns]
  );

  const isAllFilter = useMemo(
    () => visibleColumns.length === DEFAULT_COLUMN_ORDER.length,
    [visibleColumns]
  );

  const setDefaultFilter = useCallback(() => {
    setTableState((prev) => ({
      ...prev,
      visibleColumns: DEFAULT_VISIBLE_COLUMNS,
    }));
  }, [setTableState]);

  const setAllFilter = useCallback(() => {
    setTableState((prev) => ({
      ...prev,
      visibleColumns: DEFAULT_COLUMN_ORDER,
    }));
  }, [setTableState]);

  const toggleColumn = useCallback(
    (column: keyof TranscriptInfo, show: boolean) => {
      setTableState((prev) => {
        const current = prev.visibleColumns ?? DEFAULT_VISIBLE_COLUMNS;
        if (show && !current.includes(column)) {
          return {
            ...prev,
            visibleColumns: [...current, column],
          };
        } else if (!show) {
          return {
            ...prev,
            visibleColumns: current.filter((c) => c !== column),
          };
        }
        return prev;
      });
    },
    [setTableState]
  );

  return {
    isDefaultFilter,
    isAllFilter,
    setDefaultFilter,
    setAllFilter,
    toggleColumn,
    visibleColumns,
  };
};

export const TranscriptColumnsPopover: FC<TranscriptColumnsPopoverProps> = ({
  positionEl,
  isOpen,
  setIsOpen,
}) => {
  const {
    isDefaultFilter,
    isAllFilter,
    setDefaultFilter,
    setAllFilter,
    toggleColumn,
    visibleColumns,
  } = useTranscriptColumns();

  return (
    <PopOver
      id="transcript-choose-columns-popover"
      positionEl={positionEl}
      isOpen={isOpen}
      setIsOpen={setIsOpen}
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

      <div className={clsx(styles.columnList, "text-size-smaller")}>
        {DEFAULT_COLUMN_ORDER.map((column) => (
          <div
            key={column}
            className={clsx(styles.row)}
            onClick={() => {
              toggleColumn(column, !visibleColumns.includes(column));
            }}
          >
            <input
              type="checkbox"
              checked={visibleColumns.includes(column)}
              onChange={(e) => {
                toggleColumn(column, e.target.checked);
              }}
            />
            {COLUMN_LABELS[column]}
          </div>
        ))}
      </div>
    </PopOver>
  );
};
