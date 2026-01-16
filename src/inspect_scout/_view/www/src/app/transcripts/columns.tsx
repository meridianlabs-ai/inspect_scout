import { ColumnDef } from "@tanstack/react-table";
import clsx from "clsx";

import { ApplicationIcons } from "../../components/icons";
import { FilterType } from "../../state/store";
import { TranscriptInfo } from "../../types/api-types";
import { printArray } from "../../utils/array";
import { formatNumber, formatPrettyDecimal } from "../../utils/format";
import { printObject } from "../../utils/object";

export type TranscriptColumn = ColumnDef<TranscriptInfo> & {
  meta?: {
    align?: "left" | "center" | "right";
    filterable?: boolean;
    filterType?: FilterType;
  };
  /** Returns string for tooltip display */
  titleValue?: (value: unknown) => string;
  /** Returns string representation for column width measurement. Return null to skip content measurement. */
  textValue?: (value: unknown) => string | null;
  /** Minimum column width in pixels */
  minSize?: number;
  /** Maximum column width in pixels */
  maxSize?: number;
};

// Helper to create strongly-typed columns
function createColumn<K extends keyof TranscriptInfo>(config: {
  accessorKey: K;
  header: string;
  size?: number;
  minSize?: number;
  maxSize?: number;
  meta?: {
    align?: "left" | "center" | "right";
    filterable?: boolean;
    filterType?: FilterType;
  };
  cell?: (value: TranscriptInfo[K]) => React.ReactNode;
  titleValue?: (value: TranscriptInfo[K]) => string;
  textValue?: (value: TranscriptInfo[K]) => string | null;
}): TranscriptColumn {
  // Default textValue: convert to string
  const defaultTextValue = (value: unknown): string => {
    if (value === undefined || value === null) {
      return "-";
    }
    return String(value);
  };

  return {
    accessorKey: config.accessorKey as string,
    header: config.header,
    size: config.size,
    minSize: config.minSize,
    maxSize: config.maxSize,
    meta: config.meta,
    titleValue: config.titleValue as ((value: unknown) => string) | undefined,
    textValue: config.textValue
      ? (config.textValue as (value: unknown) => string | null)
      : defaultTextValue,
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

// Helper to create columns that display JSON objects with truncated display and full tooltip
function createObjectColumn<K extends keyof TranscriptInfo>(config: {
  accessorKey: K;
  header: string;
  size?: number;
  minSize?: number;
  maxSize?: number;
  meta?: {
    align?: "left" | "center" | "right";
    filterable?: boolean;
    filterType?: FilterType;
  };
  maxDisplayLength?: number;
}): TranscriptColumn {
  const maxLength = config.maxDisplayLength ?? 1000;

  const formatObjectValue = (value: TranscriptInfo[K]): string => {
    if (!value) {
      return "-";
    }
    try {
      if (typeof value === "object") {
        return printObject(value, maxLength);
      }
      return String(value);
    } catch {
      return String(value);
    }
  };

  return createColumn({
    accessorKey: config.accessorKey,
    header: config.header,
    size: config.size,
    minSize: config.minSize,
    maxSize: config.maxSize,
    meta: config.meta,
    cell: formatObjectValue,
    textValue: formatObjectValue,
    titleValue: (value) => {
      if (!value) {
        return "";
      }
      if (typeof value === "object") {
        return JSON.stringify(value, null, 2);
      }
      return String(value);
    },
  });
}

// All available columns, keyed by their accessor key
const ALL_COLUMNS: Record<keyof TranscriptInfo, TranscriptColumn> = {
  success: createColumn({
    accessorKey: "success",
    header: "✓",
    size: 40,
    minSize: 40,
    maxSize: 60,
    meta: {
      align: "center",
      filterable: true,
      filterType: "boolean",
    },
    cell: (value) => {
      if (value === undefined || value === null) {
        return "-";
      }

      const icon = value
        ? ApplicationIcons.checkbox.checked
        : ApplicationIcons.checkbox.unchecked;

      return <i className={clsx(icon, "text-secondary")} />;
    },
    textValue: () => null,
  }),
  date: createColumn({
    accessorKey: "date",
    header: "Date",
    size: 180,
    minSize: 120,
    maxSize: 300,
    meta: {
      filterable: true,
      filterType: "date",
    },
    cell: (value) => {
      if (!value) {
        return "-";
      }
      const date = new Date(value);
      return date.toLocaleString();
    },
    textValue: (value) => {
      if (!value) {
        return "-";
      }
      const date = new Date(value as string | number);
      return date.toLocaleString();
    },
  }),
  transcript_id: createColumn({
    accessorKey: "transcript_id",
    header: "Transcript ID",
    size: 150,
    minSize: 80,
    maxSize: 400,
    meta: {
      filterable: true,
      filterType: "string",
    },
    cell: (value) => {
      return value || "-";
    },
  }),
  task_set: createColumn({
    accessorKey: "task_set",
    header: "Task Set",
    size: 150,
    minSize: 80,
    maxSize: 400,
    meta: {
      filterable: true,
      filterType: "string",
    },
  }),
  task_id: createColumn({
    accessorKey: "task_id",
    header: "Task ID",
    size: 150,
    minSize: 80,
    maxSize: 400,
    meta: {
      filterable: true,
      filterType: "string",
    },
  }),
  task_repeat: createColumn({
    accessorKey: "task_repeat",
    header: "#",
    size: 50,
    minSize: 40,
    maxSize: 100,
    meta: {
      filterable: true,
      filterType: "number",
    },
  }),
  model: createColumn({
    accessorKey: "model",
    header: "Model",
    size: 200,
    minSize: 80,
    maxSize: 400,
    meta: {
      filterable: true,
      filterType: "string",
    },
  }),
  model_options: createObjectColumn({
    accessorKey: "model_options",
    header: "Model Options",
    size: 200,
    minSize: 80,
    maxSize: 500,
    meta: {
      filterable: true,
      filterType: "string",
    },
  }),
  agent: createColumn({
    accessorKey: "agent",
    header: "Agent",
    size: 150,
    minSize: 80,
    maxSize: 400,
    meta: {
      filterable: true,
      filterType: "string",
    },
    cell: (agent) => {
      return agent || "-";
    },
  }),
  agent_args: createObjectColumn({
    accessorKey: "agent_args",
    header: "Agent Args",
    size: 200,
    minSize: 80,
    maxSize: 500,
    meta: {
      filterable: true,
      filterType: "string",
    },
  }),
  score: createColumn({
    accessorKey: "score",
    header: "Score",
    size: 100,
    minSize: 60,
    maxSize: 300,
    meta: {
      filterable: true,
      filterType: "string",
    },
    cell: (value) => {
      if (!value) {
        return "-";
      }

      if (Array.isArray(value)) {
        return printArray(value, 1000);
      } else if (typeof value === "object") {
        return printObject(value, 1000);
      } else if (typeof value === "number") {
        return formatPrettyDecimal(value);
      } else {
        return String(value);
      }
    },
    textValue: (value) => {
      if (!value) {
        return "-";
      }
      if (Array.isArray(value)) {
        return printArray(value, 1000);
      } else if (typeof value === "object") {
        return printObject(value as Record<string, unknown>, 1000);
      } else if (typeof value === "number") {
        return formatPrettyDecimal(value);
      } else {
        return String(value);
      }
    },
    titleValue: (value) => {
      if (!value) {
        return "";
      }
      if (Array.isArray(value) || typeof value === "object") {
        return JSON.stringify(value, null, 2);
      }
      return String(value);
    },
  }),
  metadata: createObjectColumn({
    accessorKey: "metadata",
    header: "Metadata",
    size: 200,
    minSize: 80,
    maxSize: 500,
    meta: {
      filterable: true,
      filterType: "string",
    },
  }),
  source_id: createColumn({
    accessorKey: "source_id",
    header: "Source ID",
    size: 150,
    minSize: 80,
    maxSize: 400,
    meta: {
      filterable: true,
      filterType: "string",
    },
    cell: (value) => {
      return value || "-";
    },
  }),
  source_type: createColumn({
    accessorKey: "source_type",
    header: "Source Type",
    size: 150,
    minSize: 80,
    maxSize: 300,
    meta: {
      filterable: true,
      filterType: "string",
    },
    cell: (value) => {
      return value || "-";
    },
  }),
  source_uri: createColumn({
    accessorKey: "source_uri",
    header: "Source URI",
    size: 300,
    minSize: 100,
    maxSize: 600,
    meta: {
      filterable: true,
      filterType: "string",
    },
    cell: (value) => {
      return value || "-";
    },
  }),
  total_tokens: createColumn({
    accessorKey: "total_tokens",
    header: "Tokens",
    size: 120,
    minSize: 60,
    maxSize: 200,
    meta: {
      filterable: true,
      filterType: "number",
    },
    cell: (value) => {
      if (value == null) {
        return "-";
      }
      return formatNumber(value);
    },
    textValue: (value) => {
      if (value == null) {
        return "-";
      }
      return formatNumber(value);
    },
  }),
  total_time: createColumn({
    accessorKey: "total_time",
    header: "Time",
    size: 120,
    minSize: 60,
    maxSize: 200,
    meta: {
      filterable: true,
      filterType: "number",
    },
    cell: (value) => {
      if (value == null) {
        return "-";
      }
      return formatPrettyDecimal(value, 0);
    },
    textValue: (value) => {
      if (value == null) {
        return "-";
      }
      return formatPrettyDecimal(value, 0);
    },
  }),
  limit: createColumn({
    accessorKey: "limit",
    header: "Limit",
    size: 100,
    minSize: 60,
    maxSize: 200,
    meta: {
      filterable: true,
      filterType: "string",
    },
    cell: (value) => {
      return value || "-";
    },
  }),
  error: createColumn({
    accessorKey: "error",
    header: "Error",
    size: 200,
    minSize: 80,
    maxSize: 500,
    meta: {
      filterable: true,
      filterType: "string",
    },
    cell: (value) => {
      return value || "-";
    },
  }),
};

// Default column order (matches current order in TranscriptsGrid)
export const DEFAULT_COLUMN_ORDER: Array<keyof TranscriptInfo> = [
  "success",
  "date",
  "transcript_id",
  "task_set",
  "task_id",
  "task_repeat",
  "model",
  "model_options",
  "agent",
  "agent_args",
  "score",
  "metadata",
  "source_id",
  "source_type",
  "source_uri",
  "total_tokens",
  "total_time",
  "limit",
  "error",
];

// Default visible columns
export const DEFAULT_VISIBLE_COLUMNS: Array<keyof TranscriptInfo> = [
  "success",
  "date",
  "task_set",
  "task_id",
  "task_repeat",
  "model",
  "score",
  "total_time",
  "total_tokens",
];

/**
 * Get columns for the TranscriptsGrid.
 * @param visibleColumnKeys - Optional list of column keys to display. If not provided, returns all columns in default order.
 * @returns Array of column definitions in the order specified or default order.
 */
export function getTranscriptColumns(
  visibleColumnKeys?: Array<keyof TranscriptInfo>
): TranscriptColumn[] {
  if (!visibleColumnKeys) {
    return DEFAULT_COLUMN_ORDER.map((key) => ALL_COLUMNS[key]);
  }

  return visibleColumnKeys.map((key) => ALL_COLUMNS[key]);
}

/**
 * Extract title value for tooltip from a cell.
 */
export function getCellTitleValue(
  cell: any,
  columnDef: TranscriptColumn
): string {
  const value = cell.getValue();

  // Use custom titleValue function if provided
  if (columnDef.titleValue) {
    return columnDef.titleValue(value);
  }

  // Default fallback
  if (value === undefined || value === null) {
    return "";
  }
  if (typeof value === "object") {
    return JSON.stringify(value, null, 2);
  }
  return String(value);
}
