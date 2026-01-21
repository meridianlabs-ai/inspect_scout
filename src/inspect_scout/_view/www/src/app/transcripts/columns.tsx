import { ColumnDef } from "@tanstack/react-table";
import clsx from "clsx";

import { ApplicationIcons } from "../../components/icons";
import { FilterType } from "../../state/store";
import { TranscriptInfo } from "../../types/api-types";
import { printArray } from "../../utils/array";
import {
  formatNumber,
  formatPrettyDecimal,
  formatTime,
} from "../../utils/format";
import { printObject } from "../../utils/object";

import styles from "./columns.module.css";

// Column headers for display (used in column picker and add filter dropdown)
export const COLUMN_LABELS: Record<keyof TranscriptInfo, string> = {
  success: "Success",
  date: "Date",
  transcript_id: "Transcript ID",
  task_set: "Task Set",
  task_id: "Task ID",
  task_repeat: "Repeat",
  model: "Model",
  model_options: "Model Options",
  agent: "Agent",
  agent_args: "Agent Args",
  score: "Score",
  metadata: "Metadata",
  source_id: "Source ID",
  source_type: "Source Type",
  source_uri: "Source URI",
  total_tokens: "Total Tokens",
  total_time: "Total Time",
  message_count: "Messages",
  limit: "Limit",
  error: "Error",
};

// Column header tooltips (matches headerTitle in column definitions)
export const COLUMN_HEADER_TITLES: Record<keyof TranscriptInfo, string> = {
  success: "Boolean reduction of score to succeeded/failed.",
  date: "The date and time when the transcript was created.",
  transcript_id:
    "Globally unique identifier for a transcript (maps to EvalSample.uuid in Inspect logs).",
  task_set:
    "Set from which transcript task was drawn (e.g. Inspect task name or benchmark name)",
  task_id: "Identifier for task (e.g. dataset sample id).",
  task_repeat: "Repeat for a given task id within a task set (e.g. epoch).",
  model: "Main model used by agent.",
  model_options: "Generation options for main model.",
  agent: "Agent used to to execute task.",
  agent_args: "Arguments passed to create agent.",
  score: "Value indicating score on task.",
  metadata:
    "Transcript source specific metadata (e.g. model, task name, errors, epoch, dataset sample id, limits, etc.).",
  source_id:
    "Globally unique identifier for a transcript source (maps to eval_id in Inspect logs)",
  source_type: 'Type of transcript source (e.g. "eval_log", "weave", etc.).',
  source_uri:
    "Globally unique identifier for a transcript source (maps to eval_id in Inspect logs)",
  total_tokens: "Tokens spent in execution of task.",
  total_time: "Time required to execute task (seconds).",
  message_count: "Total messages in conversation.",
  limit:
    'Limit that caused the task to exit (e.g. "tokens", "messages", etc.).',
  error: "Error message that terminated the task.",
};

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
  /** Tooltip text for the column header */
  headerTitle?: string;
};

// Helper to create strongly-typed columns
function createColumn<K extends keyof TranscriptInfo>(config: {
  accessorKey: K;
  header: string;
  headerTitle?: string;
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
    headerTitle: config.headerTitle,
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
  headerTitle?: string;
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
    headerTitle: config.headerTitle,
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
    headerTitle: "Boolean reduction of score to succeeded/failed.",
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

      return (
        <i
          className={clsx(
            icon,
            "text-secondary",
            value ? styles.success : styles.unsuccess
          )}
        />
      );
    },
    textValue: () => null,
  }),
  date: createColumn({
    accessorKey: "date",
    header: "Date",
    headerTitle: "The date and time when the transcript was created.",
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
    headerTitle:
      "Globally unique identifier for a transcript (maps to EvalSample.uuid in Inspect logs).",
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
    headerTitle:
      "Set from which transcript task was drawn (e.g. Inspect task name or benchmark name)",
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
    headerTitle: "Identifier for task (e.g. dataset sample id).",
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
    headerTitle: "Repeat for a given task id within a task set (e.g. epoch).",
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
    headerTitle: "Main model used by agent.",
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
    headerTitle: "Generation options for main model.",
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
    headerTitle: "Agent used to to execute task.",
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
    headerTitle: "Arguments passed to create agent.",
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
    headerTitle: "Value indicating score on task.",
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
    headerTitle:
      "Transcript source specific metadata (e.g. model, task name, errors, epoch, dataset sample id, limits, etc.).",
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
    headerTitle:
      "Globally unique identifier for a transcript source (maps to eval_id in Inspect logs)",
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
    headerTitle: "Type of transcript source (e.g. “eval_log”, “weave”, etc.).",
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
    headerTitle:
      "Globally unique identifier for a transcript source (maps to eval_id in Inspect logs)",
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
    headerTitle: "Tokens spent in execution of task.",
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
    headerTitle: "Time required to execute task (seconds).",
    size: 120,
    minSize: 60,
    maxSize: 200,
    meta: {
      filterable: true,
      filterType: "duration",
    },
    cell: (value) => {
      if (value == null) {
        return "-";
      }
      return formatTime(value);
    },
    textValue: (value) => {
      if (value == null) {
        return "-";
      }
      return formatTime(value);
    },
  }),
  message_count: createColumn({
    accessorKey: "message_count",
    header: "Messages",
    headerTitle: "Total messages in conversation.",
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
  limit: createColumn({
    accessorKey: "limit",
    header: "Limit",
    headerTitle:
      "Limit that caused the task to exit (e.g. “tokens”, “messages, etc.).",
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
    headerTitle: "Error message that terminated the task.",
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
  "message_count",
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
  "message_count",
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

/**
 * Get the filter type for a given column ID.
 * @param columnId - The column ID to look up
 * @returns The filter type for the column, or "string" as default
 */
export function getFilterTypeForColumn(columnId: string): FilterType {
  const column = ALL_COLUMNS[columnId as keyof TranscriptInfo];
  return column?.meta?.filterType ?? "string";
}
