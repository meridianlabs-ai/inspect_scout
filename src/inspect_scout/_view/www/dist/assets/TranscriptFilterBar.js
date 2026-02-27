import { a as useApi, b as useAsyncDataFromQuery, s as skipToken, r as reactExports, j as jsxRuntimeExports, c as clsx, A as ApplicationIcons, u as useStore } from "./index.js";
import { u as useFilterConditions } from "./useFilterConditions.js";
import { u as useFilterBarHandlers, a as useAddFilterPopover, F as FilterBar } from "./useFilterBarHandlers.js";
import "./transcriptColumns.js";
import { p as printArray } from "./array.js";
import { f as formatNumber, e as formatTime, a as formatPrettyDecimal } from "./ToolButton.js";
import { p as printObject } from "./object.js";
const useCode = (condition) => {
  const api = useApi();
  return useAsyncDataFromQuery({
    queryKey: ["code", condition],
    queryFn: condition === skipToken ? skipToken : () => api.postCode(condition),
    staleTime: Infinity
  });
};
const useTranscriptsColumnValues = (params) => {
  const api = useApi();
  return useAsyncDataFromQuery({
    queryKey: params === skipToken ? [skipToken] : ["transcriptsColumnValues", params],
    queryFn: params === skipToken ? skipToken : () => api.getTranscriptsColumnValues(
      params.location,
      params.column,
      params.filter
    ),
    staleTime: 10 * 60 * 1e3
    // We can be pretty liberal here
  });
};
const useTranscriptsFilterBarProps = (transcriptsDir) => {
  const [editingColumnId, setEditingColumnId] = reactExports.useState(null);
  const condition = useFilterConditions();
  const otherColumnsFilter = useFilterConditions(editingColumnId ?? void 0);
  const { data: filterCodeValues } = useCode(condition ?? skipToken);
  const { data: filterSuggestions } = useTranscriptsColumnValues(
    editingColumnId && transcriptsDir ? {
      location: transcriptsDir,
      column: editingColumnId,
      filter: otherColumnsFilter
    } : skipToken
  );
  const onFilterColumnChange = reactExports.useCallback(
    (columnId) => setEditingColumnId(columnId),
    []
  );
  return {
    filterCodeValues,
    filterSuggestions: filterSuggestions ?? [],
    onFilterColumnChange,
    condition
  };
};
const success = "_success_1mf4d_1";
const unsuccess = "_unsuccess_1mf4d_5";
const styles = {
  success,
  unsuccess
};
const COLUMN_LABELS = {
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
  error: "Error"
};
const COLUMN_HEADER_TITLES = {
  success: "Boolean reduction of score to succeeded/failed.",
  date: "The date and time when the transcript was created.",
  transcript_id: "Globally unique identifier for a transcript (maps to EvalSample.uuid in Inspect logs).",
  task_set: "Set from which transcript task was drawn (e.g. Inspect task name or benchmark name)",
  task_id: "Identifier for task (e.g. dataset sample id).",
  task_repeat: "Repeat for a given task id within a task set (e.g. epoch).",
  model: "Main model used by agent.",
  model_options: "Generation options for main model.",
  agent: "Agent used to to execute task.",
  agent_args: "Arguments passed to create agent.",
  score: "Value indicating score on task.",
  metadata: "Transcript source specific metadata (e.g. model, task name, errors, epoch, dataset sample id, limits, etc.).",
  source_id: "Globally unique identifier for a transcript source (maps to eval_id in Inspect logs)",
  source_type: 'Type of transcript source (e.g. "eval_log", "weave", etc.).',
  source_uri: "Globally unique identifier for a transcript source (maps to eval_id in Inspect logs)",
  total_tokens: "Tokens spent in execution of task.",
  total_time: "Time required to execute task (seconds).",
  message_count: "Total messages in conversation.",
  limit: 'Limit that caused the task to exit (e.g. "tokens", "messages", etc.).',
  error: "Error message that terminated the task."
};
function createColumn(config) {
  const defaultTextValue = (value) => {
    if (value === void 0 || value === null) {
      return "-";
    }
    return String(value);
  };
  return {
    accessorKey: config.accessorKey,
    header: config.header,
    headerTitle: config.headerTitle,
    size: config.size,
    minSize: config.minSize,
    maxSize: config.maxSize,
    meta: config.meta,
    titleValue: config.titleValue,
    textValue: config.textValue ? config.textValue : defaultTextValue,
    cell: (info) => {
      const value = info.getValue();
      if (config.cell) {
        return config.cell(value);
      }
      if (value === void 0 || value === null) {
        return "-";
      }
      return String(value);
    }
  };
}
function createObjectColumn(config) {
  const maxLength = config.maxDisplayLength ?? 1e3;
  const formatObjectValue = (value) => {
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
    }
  });
}
const ALL_COLUMNS = {
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
      filterType: "boolean"
    },
    cell: (value) => {
      if (value === void 0 || value === null) {
        return "-";
      }
      const icon = value ? ApplicationIcons.checkbox.checked : ApplicationIcons.checkbox.unchecked;
      return /* @__PURE__ */ jsxRuntimeExports.jsx(
        "i",
        {
          className: clsx(
            icon,
            "text-secondary",
            value ? styles.success : styles.unsuccess
          )
        }
      );
    },
    textValue: () => null
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
      filterType: "date"
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
      const date = new Date(value);
      return date.toLocaleString();
    }
  }),
  transcript_id: createColumn({
    accessorKey: "transcript_id",
    header: "Transcript ID",
    headerTitle: "Globally unique identifier for a transcript (maps to EvalSample.uuid in Inspect logs).",
    size: 150,
    minSize: 80,
    maxSize: 400,
    meta: {
      filterable: true,
      filterType: "string"
    },
    cell: (value) => {
      return value || "-";
    }
  }),
  task_set: createColumn({
    accessorKey: "task_set",
    header: "Task Set",
    headerTitle: "Set from which transcript task was drawn (e.g. Inspect task name or benchmark name)",
    size: 150,
    minSize: 80,
    maxSize: 400,
    meta: {
      filterable: true,
      filterType: "string"
    }
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
      filterType: "string"
    }
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
      filterType: "number"
    }
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
      filterType: "string"
    }
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
      filterType: "string"
    }
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
      filterType: "string"
    },
    cell: (agent) => {
      return agent || "-";
    }
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
      filterType: "string"
    }
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
      filterType: "string"
    },
    cell: (value) => {
      if (!value) {
        return "-";
      }
      if (Array.isArray(value)) {
        return printArray(value, 1e3);
      } else if (typeof value === "object") {
        return printObject(value, 1e3);
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
        return printArray(value, 1e3);
      } else if (typeof value === "object") {
        return printObject(value, 1e3);
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
    }
  }),
  metadata: createObjectColumn({
    accessorKey: "metadata",
    header: "Metadata",
    headerTitle: "Transcript source specific metadata (e.g. model, task name, errors, epoch, dataset sample id, limits, etc.).",
    size: 200,
    minSize: 80,
    maxSize: 500,
    meta: {
      filterable: true,
      filterType: "string"
    }
  }),
  source_id: createColumn({
    accessorKey: "source_id",
    header: "Source ID",
    headerTitle: "Globally unique identifier for a transcript source (maps to eval_id in Inspect logs)",
    size: 150,
    minSize: 80,
    maxSize: 400,
    meta: {
      filterable: true,
      filterType: "string"
    },
    cell: (value) => {
      return value || "-";
    }
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
      filterType: "string"
    },
    cell: (value) => {
      return value || "-";
    }
  }),
  source_uri: createColumn({
    accessorKey: "source_uri",
    header: "Source URI",
    headerTitle: "Globally unique identifier for a transcript source (maps to eval_id in Inspect logs)",
    size: 300,
    minSize: 100,
    maxSize: 600,
    meta: {
      filterable: true,
      filterType: "string"
    },
    cell: (value) => {
      return value || "-";
    }
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
      filterType: "number"
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
    }
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
      filterType: "duration"
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
    }
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
      filterType: "number"
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
    }
  }),
  limit: createColumn({
    accessorKey: "limit",
    header: "Limit",
    headerTitle: "Limit that caused the task to exit (e.g. “tokens”, “messages, etc.).",
    size: 100,
    minSize: 60,
    maxSize: 200,
    meta: {
      filterable: true,
      filterType: "string"
    },
    cell: (value) => {
      return value || "-";
    }
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
      filterType: "string"
    },
    cell: (value) => {
      return value || "-";
    }
  })
};
const DEFAULT_COLUMN_ORDER = [
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
  "error"
];
const DEFAULT_VISIBLE_COLUMNS = [
  "success",
  "date",
  "task_set",
  "task_id",
  "task_repeat",
  "model",
  "score",
  "message_count",
  "total_time",
  "total_tokens"
];
function getTranscriptColumns(visibleColumnKeys) {
  if (!visibleColumnKeys) {
    return DEFAULT_COLUMN_ORDER.map((key) => ALL_COLUMNS[key]);
  }
  return visibleColumnKeys.map((key) => ALL_COLUMNS[key]);
}
const FILTER_COLUMNS = DEFAULT_COLUMN_ORDER.map(
  (columnId) => ({
    id: columnId,
    label: COLUMN_LABELS[columnId],
    filterType: ALL_COLUMNS[columnId].meta?.filterType ?? "string"
  })
);
const COLUMNS_INFO = DEFAULT_COLUMN_ORDER.map((key) => ({
  id: key,
  label: COLUMN_LABELS[key],
  headerTitle: COLUMN_HEADER_TITLES[key]
}));
const TranscriptFilterBar = ({
  filterCodeValues,
  filterSuggestions = [],
  onFilterColumnChange,
  includeColumnPicker = true
}) => {
  const filters = useStore(
    (state) => state.transcriptsTableState.columnFilters
  );
  const visibleColumns = useStore(
    (state) => state.transcriptsTableState.visibleColumns
  );
  const setTranscriptsTableState = useStore(
    (state) => state.setTranscriptsTableState
  );
  const { handleFilterChange, removeFilter, handleAddFilter } = useFilterBarHandlers({
    setTableState: setTranscriptsTableState,
    defaultVisibleColumns: DEFAULT_VISIBLE_COLUMNS
  });
  const handleVisibleColumnsChange = reactExports.useCallback(
    (newVisibleColumns) => {
      setTranscriptsTableState((prevState) => ({
        ...prevState,
        visibleColumns: newVisibleColumns
      }));
    },
    [setTranscriptsTableState]
  );
  const addFilterPopover = useAddFilterPopover({
    columns: FILTER_COLUMNS,
    filters,
    onAddFilter: handleAddFilter,
    onFilterColumnChange
  });
  return /* @__PURE__ */ jsxRuntimeExports.jsx(
    FilterBar,
    {
      filters,
      onFilterChange: handleFilterChange,
      onRemoveFilter: removeFilter,
      filterCodeValues: filterCodeValues ?? {},
      filterSuggestions,
      onFilterColumnChange,
      popoverIdPrefix: "transcript",
      addFilterPopoverState: addFilterPopover,
      columns: includeColumnPicker ? COLUMNS_INFO : void 0,
      visibleColumns: visibleColumns ?? DEFAULT_VISIBLE_COLUMNS,
      defaultVisibleColumns: DEFAULT_VISIBLE_COLUMNS,
      onVisibleColumnsChange: includeColumnPicker ? handleVisibleColumnsChange : void 0
    }
  );
};
export {
  DEFAULT_COLUMN_ORDER as D,
  TranscriptFilterBar as T,
  getTranscriptColumns as g,
  useTranscriptsFilterBarProps as u
};
//# sourceMappingURL=TranscriptFilterBar.js.map
