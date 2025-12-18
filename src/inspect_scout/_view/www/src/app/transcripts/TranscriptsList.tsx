import {
  useReactTable,
  getCoreRowModel,
  ColumnDef,
  flexRender,
} from "@tanstack/react-table";
import { useVirtualizer } from "@tanstack/react-virtual";
import clsx from "clsx";
import { FC, useRef, useMemo } from "react";

import { TranscriptInfo } from "../../types";
import { printArray } from "../../utils/array";
import { formatNumber, formatPrettyDecimal } from "../../utils/format";
import { printObject } from "../../utils/object";
import { ApplicationIcons } from "../appearance/icons";

import styles from "./TranscriptsList.module.css";

type TranscriptColumn = ColumnDef<TranscriptInfo> & {
  meta?: {
    align?: "left" | "center" | "right";
  };
};

// Helper to create strongly-typed columns
function createColumn<K extends keyof TranscriptInfo>(config: {
  accessorKey: K;
  header: string;
  size?: number;
  meta?: { align?: "left" | "center" | "right" };
  cell?: (value: TranscriptInfo[K]) => React.ReactNode;
}): TranscriptColumn {
  return {
    accessorKey: config.accessorKey as string,
    header: config.header,
    size: config.size,
    meta: config.meta,
    cell: (info) => {
      const value = info.getValue() as TranscriptInfo[K];
      if (config.cell) {
        return config.cell(value);
      }
      if (value === undefined || value === null) {
        return "-";
      }
      return String(value);
    },
  };
}

interface TranscriptsListProps {
  transcripts?: TranscriptInfo[];
  className?: string | string[];
}

export const TranscriptsList: FC<TranscriptsListProps> = ({
  transcripts = [],
  className,
}) => {
  const parentRef = useRef<HTMLDivElement>(null);

  // Define table columns
  const columns = useMemo<TranscriptColumn[]>(
    () => [
      createColumn({
        accessorKey: "success",
        header: "Success",
        size: 68,
        meta: {
          align: "center",
        },
        cell: (value) => {
          // value is now strongly typed as boolean | undefined
          if (value === undefined) {
            return "-";
          }

          const icon = value
            ? ApplicationIcons.success
            : ApplicationIcons.error;
          const colorCls = value ? styles.green : styles.red;

          return <i className={clsx(icon, colorCls)} />;
        },
      }),
      createColumn({
        accessorKey: "task_set",
        header: "Task Set",
        size: 150,
      }),
      createColumn({
        accessorKey: "task_id",
        header: "Task ID",
        size: 150,
      }),
      createColumn({
        accessorKey: "task_repeat",
        header: "Repeat",
        size: 80,
      }),
      createColumn({
        accessorKey: "model",
        header: "Model",
        size: 200,
      }),
      createColumn({
        accessorKey: "score",
        header: "Score",
        size: 100,
        cell: (value) => {
          if (!value) {
            return "-";
          }

          const scoreValue = value.value;
          if (Array.isArray(scoreValue)) {
            return printArray(scoreValue, 1000);
          } else if (typeof scoreValue === "object") {
            return printObject(scoreValue, 1000);
          } else if (typeof scoreValue === "number") {
            return formatPrettyDecimal(scoreValue);
          } else {
            return String(scoreValue);
          }
        },
      }),
      createColumn({
        accessorKey: "total_tokens",
        header: "Total Tokens",
        size: 120,
        cell: (value) => {
          if (value === undefined) {
            return "-";
          }
          return formatNumber(value);
        },
      }),
      createColumn({
        accessorKey: "total_time",
        header: "Total Time",
        size: 120,
        cell: (value) => {
          if (value === undefined) {
            return "-";
          }
          return formatPrettyDecimal(value);
        },
      }),
    ],
    []
  );

  // Create table instance
  const table = useReactTable({
    data: transcripts,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  const { rows } = table.getRowModel();

  // Create virtualizer
  const rowVirtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => parentRef.current,
    // Estimated row height in pixels
    estimateSize: () => 28,
    // Number of items to render outside visible area
    overscan: 10,
  });

  const virtualItems = rowVirtualizer.getVirtualItems();
  const totalSize = rowVirtualizer.getTotalSize();

  return (
    <div ref={parentRef} className={clsx(className, styles.container)}>
      <table className={styles.table}>
        <thead className={styles.thead}>
          {table.getHeaderGroups().map((headerGroup) => (
            <tr key={headerGroup.id} className={styles.headerRow}>
              {headerGroup.headers.map((header) => {
                const align = (header.column.columnDef as TranscriptColumn).meta
                  ?.align;
                return (
                  <th
                    key={header.id}
                    className={clsx(
                      styles.headerCell,
                      align === "center" && styles.headerCellCenter
                    )}
                    style={{ width: header.getSize() }}
                  >
                    {header.isPlaceholder
                      ? null
                      : flexRender(
                          header.column.columnDef.header,
                          header.getContext()
                        )}
                    <div className={styles.headerSeparator} />
                  </th>
                );
              })}
            </tr>
          ))}
        </thead>
        <tbody className={styles.tbody} style={{ height: `${totalSize}px` }}>
          {virtualItems.map((virtualRow) => {
            const row = rows[virtualRow.index];
            if (!row) return null;

            return (
              <tr
                key={row.id}
                className={styles.row}
                style={{ transform: `translateY(${virtualRow.start}px)` }}
              >
                {row.getVisibleCells().map((cell) => {
                  const align = (cell.column.columnDef as TranscriptColumn).meta
                    ?.align;
                  return (
                    <td
                      key={cell.id}
                      className={clsx(
                        styles.cell,
                        align === "center" && styles.cellCenter
                      )}
                      style={{ width: cell.column.getSize() }}
                    >
                      {flexRender(
                        cell.column.columnDef.cell,
                        cell.getContext()
                      )}
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};
