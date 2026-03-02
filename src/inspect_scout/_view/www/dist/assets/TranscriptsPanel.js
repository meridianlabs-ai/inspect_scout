import { u as useStore, r as reactExports, j as jsxRuntimeExports, D as transcriptRoute, e as useAppConfig, c as clsx, L as LoadingBar, f as ErrorPanel, s as skipToken } from "./index.js";
import { u as useDocumentTitle } from "./useDocumentTitle.js";
import { F as Footer } from "./Footer.js";
import { T as TranscriptsNavbar } from "./useFilterConditions.js";
import { g as getTranscriptColumns, D as DEFAULT_COLUMN_ORDER, u as useTranscriptsFilterBarProps, T as TranscriptFilterBar } from "./TranscriptFilterBar.js";
import { u as useServerTranscriptsInfinite, T as TRANSCRIPTS_INFINITE_SCROLL_CONFIG } from "./constants.js";
import { u as useTranscriptsDir } from "./useTranscriptsDir.js";
import { g as getColumnConstraints, c as clampSize, a as getSizingStrategy, D as DataGrid } from "./strategies.js";
import "./_commonjsHelpers.js";
import "./ToolButton.js";
import "./Navbar.js";
import "./useFilterBarHandlers.js";
import "./ToolDropdownButton.js";
import "./Chip.js";
import "./transcriptColumns.js";
import "./array.js";
import "./object.js";
import "./index2.js";
function useColumnSizing({
  columns,
  tableRef,
  data
}) {
  const columnSizing = useStore(
    (state) => state.transcriptsTableState.columnSizing
  );
  const sizingStrategy = useStore(
    (state) => state.transcriptsTableState.sizingStrategy
  );
  const manuallyResizedColumns = useStore(
    (state) => state.transcriptsTableState.manuallyResizedColumns
  );
  const setTableState = useStore((state) => state.setTranscriptsTableState);
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
function transcriptItemKey(index, item) {
  if (!item) {
    return String(index);
  }
  return `${item.source_uri}/${item.transcript_id}`;
}
const TranscriptsGrid = ({
  transcripts,
  transcriptsDir,
  className,
  onScrollNearEnd,
  hasMore,
  fetchThreshold,
  loading,
  filterSuggestions = [],
  onFilterColumnChange
}) => {
  const tableRef = reactExports.useRef(null);
  const columnOrder = useStore(
    (state) => state.transcriptsTableState.columnOrder
  );
  const sorting = useStore((state) => state.transcriptsTableState.sorting);
  const rowSelection = useStore(
    (state) => state.transcriptsTableState.rowSelection
  );
  const columnFilters = useStore((state) => state.transcriptsTableState.columnFilters) ?? {};
  const focusedRowId = useStore(
    (state) => state.transcriptsTableState.focusedRowId
  );
  const visibleColumns = useStore((state) => state.transcriptsTableState.visibleColumns) ?? DEFAULT_VISIBLE_COLUMNS;
  const setTableState = useStore((state) => state.setTranscriptsTableState);
  const columns = reactExports.useMemo(
    () => getTranscriptColumns(visibleColumns),
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
    data: transcripts
  });
  const hasInitializedRef = reactExports.useRef(false);
  const previousVisibleColumnsRef = reactExports.useRef(null);
  reactExports.useEffect(() => {
    if (!hasInitializedRef.current && transcripts.length > 0) {
      hasInitializedRef.current = true;
      applyAutoSizing();
    }
  }, [transcripts.length, applyAutoSizing]);
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
    return DEFAULT_COLUMN_ORDER.filter((col) => visibleColumns.includes(col));
  }, [columnOrder, visibleColumns]);
  const getRowId = (row) => String(row.transcript_id);
  const getRowRoute = (row) => {
    if (!transcriptsDir) return "";
    return transcriptRoute(transcriptsDir, String(row.transcript_id));
  };
  return /* @__PURE__ */ jsxRuntimeExports.jsx(
    DataGrid,
    {
      data: transcripts,
      columns,
      getRowId,
      getRowKey: transcriptItemKey,
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
      emptyMessage: "No matching transcripts",
      noConfigMessage: "No transcripts directory configured."
    }
  );
};
const container = "_container_w24zj_1";
const styles = {
  container
};
const TranscriptsPanel = () => {
  useDocumentTitle("Transcripts");
  const {
    displayTranscriptsDir,
    resolvedTranscriptsDir,
    resolvedTranscriptsDirSource,
    setTranscriptsDir
  } = useTranscriptsDir();
  const config = useAppConfig();
  const filter = Array.isArray(config.filter) ? config.filter.join(" ") : config.filter;
  const sorting = useStore((state) => state.transcriptsTableState.sorting);
  const clearTranscriptState = useStore((state) => state.clearTranscriptState);
  reactExports.useEffect(() => {
    clearTranscriptState();
  }, [clearTranscriptState]);
  const {
    filterCodeValues,
    filterSuggestions,
    onFilterColumnChange,
    condition
  } = useTranscriptsFilterBarProps(resolvedTranscriptsDir);
  const { data, error, fetchNextPage, hasNextPage, isFetching } = useServerTranscriptsInfinite(
    resolvedTranscriptsDir ? {
      location: resolvedTranscriptsDir,
      pageSize: TRANSCRIPTS_INFINITE_SCROLL_CONFIG.pageSize,
      filter: condition,
      sorting
    } : skipToken
  );
  const transcripts = reactExports.useMemo(
    () => data?.pages.flatMap((page) => page.items) ?? [],
    [data]
  );
  const handleScrollNearEnd = reactExports.useCallback(
    (distanceFromBottom) => {
      if (distanceFromBottom <= 0) {
        console.log("Hit bottom!");
      }
      fetchNextPage({ cancelRefetch: false }).catch(console.error);
    },
    [fetchNextPage]
  );
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: clsx(styles.container), children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx(
      TranscriptsNavbar,
      {
        bordered: true,
        transcriptsDir: displayTranscriptsDir,
        transcriptsDirSource: resolvedTranscriptsDirSource,
        filter,
        setTranscriptsDir
      }
    ),
    /* @__PURE__ */ jsxRuntimeExports.jsx(LoadingBar, { loading: isFetching }),
    error && /* @__PURE__ */ jsxRuntimeExports.jsx(
      ErrorPanel,
      {
        title: "Error Loading Transcript",
        error: {
          message: error.message || "Unknown Error"
        }
      }
    ),
    !error && /* @__PURE__ */ jsxRuntimeExports.jsxs(jsxRuntimeExports.Fragment, { children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        TranscriptFilterBar,
        {
          filterCodeValues,
          filterSuggestions,
          onFilterColumnChange
        }
      ),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        TranscriptsGrid,
        {
          transcripts,
          transcriptsDir: resolvedTranscriptsDir,
          loading: isFetching && transcripts.length === 0,
          onScrollNearEnd: handleScrollNearEnd,
          hasMore: hasNextPage,
          fetchThreshold: TRANSCRIPTS_INFINITE_SCROLL_CONFIG.threshold,
          filterSuggestions,
          onFilterColumnChange
        }
      )
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsx(
      Footer,
      {
        id: "transcripts-footer",
        itemCount: data?.pages[0]?.total_count || 0,
        paginated: false
      }
    )
  ] });
};
export {
  TranscriptsPanel
};
//# sourceMappingURL=TranscriptsPanel.js.map
