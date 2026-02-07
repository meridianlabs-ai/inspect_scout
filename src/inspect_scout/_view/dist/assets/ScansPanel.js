import { l as useStore, u as useApi, a as useAsyncDataFromQuery, y as skipToken, r as reactExports, bN as keepPreviousData, j as jsxRuntimeExports, e as ApplicationIcons, g as clsx, t as toRelativePath, bO as scanRoute, f as useAppConfig, v as ExtendedFindProvider, E as ErrorPanel } from "./index.js";
import { d as formatNumber, L as LoadingBar } from "./ToolButton.js";
import { N as NoContentsPanel } from "./NoContentsPanel.js";
import { u as useDocumentTitle } from "./useDocumentTitle.js";
import { F as Footer } from "./Footer.js";
import { u as useScansDir, S as ScansNavbar } from "./useScansDir.js";
import { s as sortingStateToOrderBy, u as useInfiniteQuery } from "./index2.js";
import { u as useFilterBarHandlers, a as useAddFilterPopover, F as FilterBar } from "./useFilterBarHandlers.js";
import "./transcriptColumns.js";
import { p as printObject } from "./object.js";
import { g as getColumnConstraints, c as clampSize, a as getSizingStrategy, D as DataGrid } from "./strategies.js";
import "./_commonjsHelpers.js";
import "./ToolDropdownButton.js";
import "./Chip.js";
const useScanFilterConditions = (excludeColumnId) => {
  const columnFilters = useStore((state) => state.scansTableState.columnFilters) ?? {};
  const filterConditions = Object.values(columnFilters).filter((filter) => !excludeColumnId || filter.columnId !== excludeColumnId).map((filter) => filter.condition).filter((condition2) => Boolean(condition2));
  const condition = filterConditions.reduce(
    (acc, condition2) => acc ? acc.and(condition2) : condition2,
    void 0
  );
  return condition;
};
const useScansColumnValues = (params) => {
  const api = useApi();
  return useAsyncDataFromQuery({
    queryKey: params === skipToken ? [skipToken] : ["scansColumnValues", params, "scans-inv"],
    queryFn: params === skipToken ? skipToken : () => api.getScansColumnValues(
      params.location,
      params.column,
      params.filter
    ),
    staleTime: 10 * 60 * 1e3
    // We can be pretty liberal here
  });
};
const useScansFilterBarProps = (scansDir) => {
  const [editingColumnId, setEditingColumnId] = reactExports.useState(null);
  const otherColumnsFilter = useScanFilterConditions(
    editingColumnId ?? void 0
  );
  const { data: filterSuggestions } = useScansColumnValues(
    editingColumnId && scansDir ? {
      location: scansDir,
      column: editingColumnId,
      filter: otherColumnsFilter
    } : skipToken
  );
  const onFilterColumnChange = reactExports.useCallback(
    (columnId) => setEditingColumnId(columnId),
    []
  );
  return {
    filterSuggestions: filterSuggestions ?? [],
    onFilterColumnChange
  };
};
const useScansInfinite = (scansDir, pageSize = 50, filter, sorting) => {
  const api = useApi();
  const orderBy = reactExports.useMemo(
    () => sorting ? sortingStateToOrderBy(sorting) : void 0,
    [sorting]
  );
  return useInfiniteQuery({
    queryKey: [
      "scans-infinite",
      scansDir,
      filter,
      orderBy,
      pageSize,
      "scans-inv"
    ],
    queryFn: async ({ pageParam }) => {
      const pagination = pageParam ? { limit: pageSize, cursor: pageParam, direction: "forward" } : { limit: pageSize, cursor: null, direction: "forward" };
      return await api.getScans(scansDir, filter, orderBy, pagination);
    },
    initialPageParam: void 0,
    getNextPageParam: (lastPage) => lastPage.next_cursor ?? void 0,
    staleTime: 1e4,
    refetchInterval: 1e4,
    placeholderData: keepPreviousData
  });
};
const SCANS_INFINITE_SCROLL_CONFIG = {
  /** Number of rows to fetch per page (500 rows = 14,500px at 29px/row) */
  pageSize: 500,
  /** Distance from bottom (in px) at which to trigger fetch (~69 rows) */
  threshold: 2e3
};
const green = "_green_ynv0j_1";
const yellow = "_yellow_ynv0j_5";
const red = "_red_ynv0j_9";
const blue = "_blue_ynv0j_13";
const styles$1 = {
  green,
  yellow,
  red,
  blue
};
const COLUMN_LABELS = {
  // Original columns
  status: "Status",
  scan_name: "Name",
  scanners: "Scanners",
  scan_id: "Scan ID",
  model: "Model",
  location: "Path",
  timestamp: "Time",
  // New columns from spec
  scan_file: "Scan File",
  tags: "Tags",
  revision_version: "Version",
  revision_commit: "Commit",
  revision_origin: "Origin",
  packages: "Packages",
  metadata: "Metadata",
  scan_args: "Scan Args",
  transcript_count: "Transcripts",
  // Aggregated summary columns
  total_results: "Total Results",
  total_errors: "Scanner Errors",
  total_tokens: "Total Tokens"
};
const COLUMN_HEADER_TITLES = {
  // Original columns
  status: "Scan completion status (complete, in progress, or error)",
  scan_name: "Name of the scan configuration",
  scanners: "List of scanners used in this scan",
  scan_id: "Unique identifier for the scan",
  model: "Model used for scanning",
  location: "Path to the scan results",
  timestamp: "Timestamp when the scan was started",
  // New columns from spec
  scan_file: "Source file path for the scan job",
  tags: "Tags associated with this scan",
  revision_version: "Git version of the scan code",
  revision_commit: "Git commit hash of the scan code",
  revision_origin: "Git origin URL of the scan code",
  packages: "Package versions used in this scan",
  metadata: "Custom metadata for this scan",
  scan_args: "Arguments passed to the scan",
  // Aggregated summary columns
  total_results: "Total number of results across all scanners",
  total_errors: "Errors reported by scanners while processing transcripts",
  total_tokens: "Total tokens used across all scanners",
  transcript_count: "Number of transcripts processed in this scan"
};
function getStatusDisplay(scan) {
  switch (scan.status) {
    case "complete":
      return { icon: ApplicationIcons.success, colorClass: styles$1.green };
    case "error":
      return { icon: ApplicationIcons.error, colorClass: styles$1.red };
    case "active":
    case "incomplete":
    default:
      return { icon: ApplicationIcons.pendingTask, colorClass: styles$1.yellow };
  }
}
function formatObjectValue(value, maxLength = 1e3) {
  if (!value || Object.keys(value).length === 0) {
    return "-";
  }
  try {
    return printObject(value, maxLength);
  } catch {
    return "-";
  }
}
function getObjectTitleValue(value) {
  if (!value || Object.keys(value).length === 0) {
    return "";
  }
  return JSON.stringify(value, null, 2);
}
const ALL_COLUMNS = {
  // ============================================
  // Original columns
  // ============================================
  status: {
    id: "status",
    accessorKey: "status",
    header: "✓",
    headerTitle: COLUMN_HEADER_TITLES.status,
    size: 70,
    minSize: 70,
    maxSize: 70,
    meta: {
      align: "center",
      filterable: true,
      filterType: "string"
    },
    cell: (info) => {
      const scan = info.row.original;
      if (scan.active_completion_pct != null) {
        return /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: styles$1.blue, children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("i", { className: ApplicationIcons["play-circle"] }),
          " ",
          scan.active_completion_pct,
          "%"
        ] });
      }
      const { icon, colorClass } = getStatusDisplay(scan);
      return /* @__PURE__ */ jsxRuntimeExports.jsx("i", { className: clsx(icon, colorClass) });
    },
    textValue: () => null
  },
  scan_name: {
    id: "scan_name",
    accessorKey: "scan_name",
    header: "Name",
    headerTitle: COLUMN_HEADER_TITLES.scan_name,
    size: 120,
    minSize: 80,
    maxSize: 300,
    meta: {
      filterable: true,
      filterType: "string"
    }
  },
  transcript_count: {
    id: "transcript_count",
    accessorKey: "transcript_count",
    header: "Transcripts",
    headerTitle: COLUMN_HEADER_TITLES.transcript_count,
    size: 100,
    minSize: 60,
    maxSize: 200,
    meta: {
      filterable: true,
      filterType: "number"
    },
    cell: (info) => {
      const value = info.getValue();
      return formatNumber(value);
    },
    textValue: (value) => {
      return formatNumber(value);
    }
  },
  scanners: {
    id: "scanners",
    accessorKey: "scanners",
    header: "Scanners",
    headerTitle: COLUMN_HEADER_TITLES.scanners,
    size: 120,
    minSize: 80,
    maxSize: 400,
    meta: {
      filterable: true,
      filterType: "string"
    }
  },
  scan_id: {
    id: "scan_id",
    accessorKey: "scan_id",
    header: "Scan ID",
    headerTitle: COLUMN_HEADER_TITLES.scan_id,
    size: 150,
    minSize: 100,
    maxSize: 400,
    meta: {
      filterable: true,
      filterType: "string"
    }
  },
  model: {
    id: "model",
    accessorKey: "model",
    header: "Model",
    headerTitle: COLUMN_HEADER_TITLES.model,
    size: 150,
    minSize: 80,
    maxSize: 400,
    meta: {
      filterable: true,
      filterType: "string"
    }
  },
  location: {
    id: "location",
    accessorKey: "relativeLocation",
    header: "Path",
    headerTitle: COLUMN_HEADER_TITLES.location,
    size: 200,
    minSize: 100,
    maxSize: 500,
    meta: {
      filterable: true,
      filterType: "string"
    }
  },
  timestamp: {
    id: "timestamp",
    accessorKey: "timestamp",
    header: "Time",
    headerTitle: COLUMN_HEADER_TITLES.timestamp,
    size: 180,
    minSize: 120,
    maxSize: 300,
    meta: {
      filterable: true,
      filterType: "datetime"
    },
    cell: (info) => {
      const timestamp = info.getValue();
      if (!timestamp) return "-";
      return new Date(timestamp).toLocaleString();
    },
    textValue: (value) => {
      if (!value) return "-";
      return new Date(value).toLocaleString();
    }
  },
  // ============================================
  // New columns from spec
  // ============================================
  scan_file: {
    id: "scan_file",
    accessorKey: "scan_file",
    header: "Scan File",
    headerTitle: COLUMN_HEADER_TITLES.scan_file,
    size: 200,
    minSize: 100,
    maxSize: 500,
    meta: {
      filterable: true,
      filterType: "string"
    },
    cell: (info) => {
      const value = info.getValue();
      return value || "-";
    }
  },
  tags: {
    id: "tags",
    accessorKey: "tags",
    header: "Tags",
    headerTitle: COLUMN_HEADER_TITLES.tags,
    size: 150,
    minSize: 80,
    maxSize: 400,
    meta: {
      filterable: true,
      filterType: "string"
    },
    cell: (info) => {
      const value = info.getValue();
      return value || "-";
    }
  },
  revision_version: {
    id: "revision_version",
    accessorKey: "revision_version",
    header: "Version",
    headerTitle: COLUMN_HEADER_TITLES.revision_version,
    size: 150,
    minSize: 80,
    maxSize: 300,
    meta: {
      filterable: true,
      filterType: "string"
    },
    cell: (info) => {
      const value = info.getValue();
      return value || "-";
    }
  },
  revision_commit: {
    id: "revision_commit",
    accessorKey: "revision_commit",
    header: "Commit",
    headerTitle: COLUMN_HEADER_TITLES.revision_commit,
    size: 120,
    minSize: 80,
    maxSize: 300,
    meta: {
      filterable: true,
      filterType: "string"
    },
    cell: (info) => {
      const value = info.getValue();
      if (!value) return "-";
      return value.slice(0, 7);
    },
    textValue: (value) => {
      if (!value) return "-";
      const strValue = value;
      return strValue.slice(0, 7);
    }
  },
  revision_origin: {
    id: "revision_origin",
    accessorKey: "revision_origin",
    header: "Origin",
    headerTitle: COLUMN_HEADER_TITLES.revision_origin,
    size: 200,
    minSize: 100,
    maxSize: 500,
    meta: {
      filterable: true,
      filterType: "string"
    },
    cell: (info) => {
      const value = info.getValue();
      return value || "-";
    }
  },
  packages: {
    id: "packages",
    accessorKey: "packages",
    header: "Packages",
    headerTitle: COLUMN_HEADER_TITLES.packages,
    size: 200,
    minSize: 80,
    maxSize: 500,
    meta: {
      filterable: true,
      filterType: "string"
    },
    cell: (info) => {
      const value = info.getValue();
      return formatObjectValue(value);
    },
    textValue: (value) => {
      return formatObjectValue(value);
    },
    titleValue: (value) => {
      return getObjectTitleValue(value);
    }
  },
  metadata: {
    id: "metadata",
    accessorKey: "metadata",
    header: "Metadata",
    headerTitle: COLUMN_HEADER_TITLES.metadata,
    size: 200,
    minSize: 80,
    maxSize: 500,
    meta: {
      filterable: true,
      filterType: "string"
    },
    cell: (info) => {
      const value = info.getValue();
      return formatObjectValue(value);
    },
    textValue: (value) => {
      return formatObjectValue(value);
    },
    titleValue: (value) => {
      return getObjectTitleValue(value);
    }
  },
  scan_args: {
    id: "scan_args",
    accessorKey: "scan_args",
    header: "Scan Args",
    headerTitle: COLUMN_HEADER_TITLES.scan_args,
    size: 200,
    minSize: 80,
    maxSize: 500,
    meta: {
      filterable: true,
      filterType: "string"
    },
    cell: (info) => {
      const value = info.getValue();
      return formatObjectValue(value);
    },
    textValue: (value) => {
      return formatObjectValue(value);
    },
    titleValue: (value) => {
      return getObjectTitleValue(value);
    }
  },
  // ============================================
  // Aggregated summary columns
  // ============================================
  total_results: {
    id: "total_results",
    accessorKey: "total_results",
    header: "Results",
    headerTitle: COLUMN_HEADER_TITLES.total_results,
    size: 100,
    minSize: 60,
    maxSize: 200,
    meta: {
      filterable: true,
      filterType: "number"
    },
    cell: (info) => {
      const value = info.getValue();
      return formatNumber(value);
    },
    textValue: (value) => {
      return formatNumber(value);
    }
  },
  total_errors: {
    id: "total_errors",
    accessorKey: "total_errors",
    header: "Scanner Errors",
    headerTitle: COLUMN_HEADER_TITLES.total_errors,
    size: 100,
    minSize: 60,
    maxSize: 200,
    meta: {
      filterable: true,
      filterType: "number"
    },
    cell: (info) => {
      const value = info.getValue();
      return formatNumber(value);
    },
    textValue: (value) => {
      return formatNumber(value);
    }
  },
  total_tokens: {
    id: "total_tokens",
    accessorKey: "total_tokens",
    header: "Tokens",
    headerTitle: COLUMN_HEADER_TITLES.total_tokens,
    size: 120,
    minSize: 60,
    maxSize: 200,
    meta: {
      filterable: true,
      filterType: "number"
    },
    cell: (info) => {
      const value = info.getValue();
      return formatNumber(value);
    },
    textValue: (value) => {
      return formatNumber(value);
    }
  }
};
const DEFAULT_COLUMN_ORDER = [
  // Original columns first
  "status",
  "scan_name",
  "scanners",
  "scan_id",
  "model",
  "location",
  "timestamp",
  // Aggregated summary columns
  "transcript_count",
  "total_results",
  "total_errors",
  "total_tokens",
  // New columns from spec
  "scan_file",
  "tags",
  "revision_version",
  "revision_commit",
  "revision_origin",
  "packages",
  "metadata",
  "scan_args"
];
const DEFAULT_VISIBLE_COLUMNS = [
  "status",
  "scan_name",
  "scanners",
  "scan_id",
  "model",
  "location",
  "timestamp",
  "transcript_count",
  "total_results"
];
function getScanColumns(visibleColumnKeys) {
  if (!visibleColumnKeys) {
    return DEFAULT_VISIBLE_COLUMNS.map((key) => ALL_COLUMNS[key]);
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
const ScansFilterBar = ({
  includeColumnPicker = true,
  filterSuggestions = [],
  onFilterColumnChange
}) => {
  const filters = useStore((state) => state.scansTableState.columnFilters);
  const visibleColumns = useStore(
    (state) => state.scansTableState.visibleColumns
  );
  const setScansTableState = useStore((state) => state.setScansTableState);
  const { handleFilterChange, removeFilter, handleAddFilter } = useFilterBarHandlers({
    setTableState: setScansTableState,
    defaultVisibleColumns: DEFAULT_VISIBLE_COLUMNS
  });
  const addFilterPopover = useAddFilterPopover({
    columns: FILTER_COLUMNS,
    filters,
    onAddFilter: handleAddFilter,
    onFilterColumnChange
  });
  const handleVisibleColumnsChange = reactExports.useCallback(
    (newVisibleColumns) => {
      setScansTableState((prevState) => ({
        ...prevState,
        visibleColumns: newVisibleColumns
      }));
    },
    [setScansTableState]
  );
  return /* @__PURE__ */ jsxRuntimeExports.jsx(
    FilterBar,
    {
      filters,
      onFilterChange: handleFilterChange,
      onRemoveFilter: removeFilter,
      filterSuggestions,
      onFilterColumnChange,
      popoverIdPrefix: "scans",
      addFilterPopoverState: addFilterPopover,
      columns: includeColumnPicker ? COLUMNS_INFO : void 0,
      visibleColumns: visibleColumns ?? DEFAULT_VISIBLE_COLUMNS,
      defaultVisibleColumns: DEFAULT_VISIBLE_COLUMNS,
      onVisibleColumnsChange: includeColumnPicker ? handleVisibleColumnsChange : void 0
    }
  );
};
function useColumnSizing({
  columns,
  tableRef,
  data
}) {
  const columnSizing = useStore((state) => state.scansTableState.columnSizing);
  const sizingStrategy = useStore(
    (state) => state.scansTableState.sizingStrategy
  );
  const manuallyResizedColumns = useStore(
    (state) => state.scansTableState.manuallyResizedColumns
  );
  const setTableState = useStore((state) => state.setScansTableState);
  const manuallyResizedSet = reactExports.useMemo(
    () => new Set(manuallyResizedColumns),
    [manuallyResizedColumns]
  );
  const columnConstraints = reactExports.useMemo(
    () => getColumnConstraints(columns),
    [columns]
  );
  const isAutoSizingRef = reactExports.useRef(false);
  const latestRef = reactExports.useRef({
    sizingStrategy,
    columns,
    data,
    columnConstraints,
    manuallyResizedSet,
    columnSizing
  });
  reactExports.useEffect(() => {
    latestRef.current = {
      sizingStrategy,
      columns,
      data,
      columnConstraints,
      manuallyResizedSet,
      columnSizing
    };
  });
  const handleColumnSizingChange = reactExports.useCallback(
    (updaterOrValue) => {
      const newSizing = typeof updaterOrValue === "function" ? updaterOrValue(columnSizing) : updaterOrValue;
      const clampedSizing = {};
      const newManuallyResized = new Set(manuallyResizedSet);
      for (const [columnId, size] of Object.entries(newSizing)) {
        const constraints = columnConstraints.get(columnId);
        if (constraints) {
          clampedSizing[columnId] = clampSize(size, constraints);
        } else {
          clampedSizing[columnId] = size;
        }
        if (!isAutoSizingRef.current) {
          newManuallyResized.add(columnId);
        }
      }
      for (const [columnId, size] of Object.entries(columnSizing)) {
        if (!(columnId in clampedSizing)) {
          clampedSizing[columnId] = size;
        }
      }
      setTableState((prev) => ({
        ...prev,
        columnSizing: clampedSizing,
        manuallyResizedColumns: isAutoSizingRef.current ? prev.manuallyResizedColumns : Array.from(newManuallyResized)
      }));
    },
    [columnSizing, columnConstraints, manuallyResizedSet, setTableState]
  );
  const setSizingStrategy = reactExports.useCallback(
    (strategy) => {
      setTableState((prev) => ({
        ...prev,
        sizingStrategy: strategy
      }));
    },
    [setTableState]
  );
  const applyAutoSizing = reactExports.useCallback(() => {
    isAutoSizingRef.current = true;
    try {
      const {
        sizingStrategy: strategyKey,
        columns: cols,
        data: rowData,
        columnConstraints: constraints,
        manuallyResizedSet: resizedSet,
        columnSizing: currentSizing
      } = latestRef.current;
      const strategy = getSizingStrategy(
        strategyKey
      );
      const calculatedSizing = strategy.computeSizes({
        tableElement: tableRef.current,
        columns: cols,
        data: rowData,
        constraints
      });
      const newSizing = {};
      for (const [columnId, size] of Object.entries(calculatedSizing)) {
        if (resizedSet.has(columnId) && currentSizing[columnId] !== void 0) {
          newSizing[columnId] = currentSizing[columnId];
        } else {
          newSizing[columnId] = size;
        }
      }
      setTableState((prev) => ({
        ...prev,
        columnSizing: newSizing
      }));
    } finally {
      isAutoSizingRef.current = false;
    }
  }, [tableRef, setTableState]);
  const resetColumnSize = reactExports.useCallback(
    (columnId) => {
      isAutoSizingRef.current = true;
      try {
        const {
          sizingStrategy: strategyKey,
          columns: cols,
          data: rowData,
          columnConstraints: constraints
        } = latestRef.current;
        const strategy = getSizingStrategy(
          strategyKey
        );
        const allSizes = strategy.computeSizes({
          tableElement: tableRef.current,
          columns: cols,
          data: rowData,
          constraints
        });
        const newSize = allSizes[columnId];
        if (newSize !== void 0) {
          setTableState((prev) => {
            const newManuallyResized = prev.manuallyResizedColumns.filter(
              (id) => id !== columnId
            );
            return {
              ...prev,
              columnSizing: {
                ...prev.columnSizing,
                [columnId]: newSize
              },
              manuallyResizedColumns: newManuallyResized
            };
          });
        }
      } finally {
        isAutoSizingRef.current = false;
      }
    },
    [tableRef, setTableState]
  );
  const clearColumnSizing = reactExports.useCallback(() => {
    setTableState((prev) => ({
      ...prev,
      columnSizing: {},
      manuallyResizedColumns: []
    }));
  }, [setTableState]);
  return {
    columnSizing,
    setSizingStrategy,
    clearColumnSizing,
    sizingStrategy,
    handleColumnSizingChange,
    applyAutoSizing,
    resetColumnSize
  };
}
function scanItemKey(index, item) {
  if (!item) {
    return String(index);
  }
  return item.scan_id;
}
const ScansGrid = ({
  scans,
  resultsDir,
  className,
  loading,
  onScrollNearEnd,
  hasMore = false,
  fetchThreshold = 500,
  filterSuggestions = [],
  onFilterColumnChange
}) => {
  const tableRef = reactExports.useRef(null);
  const sorting = useStore((state) => state.scansTableState.sorting);
  const columnOrder = useStore((state) => state.scansTableState.columnOrder);
  const columnFilters = useStore(
    (state) => state.scansTableState.columnFilters
  );
  const rowSelection = useStore((state) => state.scansTableState.rowSelection);
  const focusedRowId = useStore((state) => state.scansTableState.focusedRowId);
  const visibleColumns = useStore(
    (state) => state.scansTableState.visibleColumns
  );
  const setTableState = useStore((state) => state.setScansTableState);
  const setVisibleScanJobCount = useStore(
    (state) => state.setVisibleScanJobCount
  );
  const data = reactExports.useMemo(
    () => scans.map((scan) => ({
      ...scan,
      relativeLocation: toRelativePath(scan.location, resultsDir)
    })),
    [scans, resultsDir]
  );
  reactExports.useEffect(() => {
    setVisibleScanJobCount(data.length);
  }, [data.length, setVisibleScanJobCount]);
  const columns = reactExports.useMemo(
    () => getScanColumns(visibleColumns),
    [visibleColumns]
  );
  const {
    columnSizing,
    handleColumnSizingChange,
    applyAutoSizing,
    resetColumnSize
  } = useColumnSizing({
    columns,
    tableRef,
    data
  });
  const hasInitializedRef = reactExports.useRef(false);
  const previousVisibleColumnsRef = reactExports.useRef(null);
  reactExports.useEffect(() => {
    if (!hasInitializedRef.current && data.length > 0) {
      hasInitializedRef.current = true;
      applyAutoSizing();
    }
  }, [data.length, applyAutoSizing]);
  reactExports.useEffect(() => {
    const previousVisibleColumns = previousVisibleColumnsRef.current;
    previousVisibleColumnsRef.current = visibleColumns;
    if (previousVisibleColumns && previousVisibleColumns !== visibleColumns) {
      applyAutoSizing();
    }
  }, [visibleColumns, applyAutoSizing]);
  const effectiveColumnOrder = reactExports.useMemo(() => {
    if (columnOrder && columnOrder.length > 0) {
      return columnOrder;
    }
    return DEFAULT_COLUMN_ORDER;
  }, [columnOrder]);
  const getRowId = (row) => row.scan_id;
  const getRowRoute = (row) => {
    if (!resultsDir) return "";
    return scanRoute(resultsDir, row.relativeLocation);
  };
  return /* @__PURE__ */ jsxRuntimeExports.jsx(
    DataGrid,
    {
      data,
      columns,
      getRowId,
      getRowKey: scanItemKey,
      state: {
        sorting,
        columnOrder: effectiveColumnOrder,
        columnFilters,
        columnSizing,
        rowSelection,
        focusedRowId
      },
      onStateChange: setTableState,
      getRowRoute,
      onScrollNearEnd,
      hasMore,
      fetchThreshold,
      filterSuggestions,
      onFilterColumnChange,
      onColumnSizingChange: handleColumnSizingChange,
      onResetColumnSize: resetColumnSize,
      className,
      loading,
      emptyMessage: "No matching scans",
      noConfigMessage: "No scans directory configured."
    }
  );
};
const container = "_container_1a52k_1";
const gridContainer = "_gridContainer_1a52k_8";
const grid = "_grid_1a52k_8";
const styles = {
  container,
  gridContainer,
  grid
};
const ScansPanel = () => {
  useDocumentTitle("Scans");
  const config = useAppConfig();
  const scanDir = config.scans.dir;
  const {
    displayScansDir,
    resolvedScansDir,
    resolvedScansDirSource,
    setScansDir
  } = useScansDir();
  const condition = useScanFilterConditions();
  const sorting = useStore((state) => state.scansTableState.sorting);
  const { filterSuggestions, onFilterColumnChange } = useScansFilterBarProps(resolvedScansDir);
  const { data, error, fetchNextPage, hasNextPage, isFetching } = useScansInfinite(
    resolvedScansDir,
    SCANS_INFINITE_SCROLL_CONFIG.pageSize,
    condition,
    sorting
  );
  const scans = reactExports.useMemo(
    () => data?.pages.flatMap((page) => page.items) ?? [],
    [data]
  );
  const handleScrollNearEnd = reactExports.useCallback(() => {
    fetchNextPage({ cancelRefetch: false }).catch(console.error);
  }, [fetchNextPage]);
  const clearScansState = useStore((state) => state.clearScansState);
  reactExports.useEffect(() => {
    clearScansState();
  }, [clearScansState]);
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: clsx(styles.container), children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx(
      ScansNavbar,
      {
        scansDir: displayScansDir,
        scansDirSource: resolvedScansDirSource,
        setScansDir,
        bordered: true
      }
    ),
    /* @__PURE__ */ jsxRuntimeExports.jsx(LoadingBar, { loading: isFetching }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs(ExtendedFindProvider, { children: [
      error && /* @__PURE__ */ jsxRuntimeExports.jsx(
        ErrorPanel,
        {
          title: "Error Loading Scans",
          error: { message: error.message }
        }
      ),
      !data && !error && /* @__PURE__ */ jsxRuntimeExports.jsx(NoContentsPanel, { icon: ApplicationIcons.running, text: "Loading..." }),
      data && !error && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles.gridContainer, children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          ScansFilterBar,
          {
            filterSuggestions,
            onFilterColumnChange
          }
        ),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          ScansGrid,
          {
            scans,
            resultsDir: scanDir,
            loading: isFetching && scans.length === 0,
            className: styles.grid,
            onScrollNearEnd: handleScrollNearEnd,
            hasMore: hasNextPage,
            fetchThreshold: SCANS_INFINITE_SCROLL_CONFIG.threshold,
            filterSuggestions,
            onFilterColumnChange
          }
        )
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        Footer,
        {
          id: "scan-job-footer",
          itemCount: data?.pages[0]?.total_count ?? 0,
          paginated: false
        }
      )
    ] })
  ] });
};
export {
  ScansPanel
};
//# sourceMappingURL=ScansPanel.js.map
