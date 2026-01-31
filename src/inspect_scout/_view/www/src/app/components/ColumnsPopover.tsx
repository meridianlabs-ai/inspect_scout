import clsx from "clsx";
import { FC, useCallback, useMemo } from "react";

import { PopOver } from "../../components/PopOver";

import styles from "./ColumnsPopover.module.css";

export interface ColumnInfo {
  id: string;
  label: string;
  headerTitle?: string;
}

export interface ColumnsPopoverProps {
  /** Popover positioning element */
  positionEl: HTMLElement | null;
  /** Whether the popover is open */
  isOpen: boolean;
  /** Callback to set open state */
  setIsOpen: (open: boolean) => void;
  /** All available columns in display order */
  columns: ColumnInfo[];
  /** Currently visible column IDs */
  visibleColumns: string[];
  /** Default visible column IDs (for "Default" link) */
  defaultVisibleColumns: string[];
  /** Callback when visible columns change */
  onVisibleColumnsChange: (columns: string[]) => void;
  /** Optional popover ID for accessibility */
  popoverId?: string;
}

export const ColumnsPopover: FC<ColumnsPopoverProps> = ({
  positionEl,
  isOpen,
  setIsOpen,
  columns,
  visibleColumns,
  defaultVisibleColumns,
  onVisibleColumnsChange,
  popoverId = "columns-popover",
}) => {
  const isDefaultSelection = useMemo(
    () =>
      visibleColumns.length === defaultVisibleColumns.length &&
      visibleColumns.every((col) => defaultVisibleColumns.includes(col)),
    [visibleColumns, defaultVisibleColumns]
  );

  const isAllSelection = useMemo(
    () => visibleColumns.length === columns.length,
    [visibleColumns, columns]
  );

  const setDefaultSelection = useCallback(() => {
    onVisibleColumnsChange(defaultVisibleColumns);
  }, [onVisibleColumnsChange, defaultVisibleColumns]);

  const setAllSelection = useCallback(() => {
    onVisibleColumnsChange(columns.map((c) => c.id));
  }, [onVisibleColumnsChange, columns]);

  const toggleColumn = useCallback(
    (columnId: string, show: boolean) => {
      if (show && !visibleColumns.includes(columnId)) {
        onVisibleColumnsChange([...visibleColumns, columnId]);
      } else if (!show) {
        onVisibleColumnsChange(visibleColumns.filter((c) => c !== columnId));
      }
    },
    [visibleColumns, onVisibleColumnsChange]
  );

  return (
    <PopOver
      id={popoverId}
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
            isDefaultSelection ? styles.selected : undefined
          )}
          onClick={() => setDefaultSelection()}
        >
          Default
        </a>
        |
        <a
          className={clsx(
            styles.link,
            isAllSelection ? styles.selected : undefined
          )}
          onClick={() => setAllSelection()}
        >
          All
        </a>
      </div>

      <div className={clsx(styles.columnList, "text-size-smaller")}>
        {columns.map((column) => (
          <div
            key={column.id}
            className={clsx(styles.row)}
            title={[column.id, column.headerTitle].filter(Boolean).join("\n")}
            onClick={() => {
              toggleColumn(column.id, !visibleColumns.includes(column.id));
            }}
          >
            <input
              type="checkbox"
              checked={visibleColumns.includes(column.id)}
              onChange={(e) => {
                toggleColumn(column.id, e.target.checked);
              }}
            />
            {column.label}
          </div>
        ))}
      </div>
    </PopOver>
  );
};
