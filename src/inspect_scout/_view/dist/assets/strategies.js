import { r as reactExports, j as jsxRuntimeExports, k as reactDomExports, n as useLoggingNavigate, c3 as openRouteInNewTab, g as clsx, e as ApplicationIcons } from "./index.js";
import { P as PopOver } from "./ToolButton.js";
import { b as useColumnFilterPopover, C as ColumnFilterButton, c as ColumnFilterEditor } from "./useFilterBarHandlers.js";
import "./transcriptColumns.js";
const headerActions = "_headerActions_uh0qk_1";
const filterPopover = "_filterPopover_uh0qk_8";
const styles$1 = {
  headerActions,
  filterPopover
};
const ColumnFilterControl = ({
  columnId,
  filterType,
  condition,
  onChange,
  suggestions = [],
  onOpenChange
}) => {
  const buttonRef = reactExports.useRef(null);
  const {
    isOpen,
    setIsOpen,
    operator,
    setOperator,
    operatorOptions,
    value: rawValue,
    setValue: setRawValue,
    value2: rawValue2,
    setValue2: setRawValue2,
    isValueDisabled,
    isRangeOperator,
    commitAndClose,
    cancelAndClose
  } = useColumnFilterPopover({
    columnId,
    filterType,
    condition,
    onChange
  });
  const handlePopoverOpenChange = reactExports.useCallback(
    (nextOpen) => {
      setIsOpen(nextOpen);
      onOpenChange?.(nextOpen ? columnId : null);
    },
    [setIsOpen, onOpenChange, columnId]
  );
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles$1.headerActions, children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx(
      ColumnFilterButton,
      {
        ref: buttonRef,
        columnId,
        isActive: !!condition,
        onClick: (event) => {
          event.stopPropagation();
          handlePopoverOpenChange(!isOpen);
        }
      }
    ),
    /* @__PURE__ */ jsxRuntimeExports.jsx(
      PopOver,
      {
        id: `transcripts-filter-${columnId}`,
        isOpen,
        setIsOpen: handlePopoverOpenChange,
        positionEl: buttonRef.current,
        placement: "bottom-end",
        showArrow: true,
        hoverDelay: -1,
        className: styles$1.filterPopover,
        closeOnMouseLeave: false,
        styles: {
          padding: "0.4rem",
          backgroundColor: "var(--bs-light)"
        },
        children: /* @__PURE__ */ jsxRuntimeExports.jsx(
          ColumnFilterEditor,
          {
            columnId,
            filterType,
            operator,
            operatorOptions,
            rawValue,
            rawValue2,
            isValueDisabled,
            isRangeOperator,
            onOperatorChange: setOperator,
            onValueChange: setRawValue,
            onValue2Change: setRawValue2,
            onCommit: commitAndClose,
            onCancel: cancelAndClose,
            suggestions
          }
        )
      }
    )
  ] });
};
function functionalUpdate(updater, input) {
  return typeof updater === "function" ? updater(input) : updater;
}
function makeStateUpdater(key, instance) {
  return (updater) => {
    instance.setState((old) => {
      return {
        ...old,
        [key]: functionalUpdate(updater, old[key])
      };
    });
  };
}
function isFunction(d) {
  return d instanceof Function;
}
function isNumberArray(d) {
  return Array.isArray(d) && d.every((val) => typeof val === "number");
}
function flattenBy(arr, getChildren) {
  const flat = [];
  const recurse = (subArr) => {
    subArr.forEach((item) => {
      flat.push(item);
      const children = getChildren(item);
      if (children != null && children.length) {
        recurse(children);
      }
    });
  };
  recurse(arr);
  return flat;
}
function memo$1(getDeps, fn, opts) {
  let deps = [];
  let result;
  return (depArgs) => {
    let depTime;
    if (opts.key && opts.debug) depTime = Date.now();
    const newDeps = getDeps(depArgs);
    const depsChanged = newDeps.length !== deps.length || newDeps.some((dep, index) => deps[index] !== dep);
    if (!depsChanged) {
      return result;
    }
    deps = newDeps;
    let resultTime;
    if (opts.key && opts.debug) resultTime = Date.now();
    result = fn(...newDeps);
    opts == null || opts.onChange == null || opts.onChange(result);
    if (opts.key && opts.debug) {
      if (opts != null && opts.debug()) {
        const depEndTime = Math.round((Date.now() - depTime) * 100) / 100;
        const resultEndTime = Math.round((Date.now() - resultTime) * 100) / 100;
        const resultFpsPercentage = resultEndTime / 16;
        const pad = (str, num) => {
          str = String(str);
          while (str.length < num) {
            str = " " + str;
          }
          return str;
        };
        console.info(`%c⏱ ${pad(resultEndTime, 5)} /${pad(depEndTime, 5)} ms`, `
            font-size: .6rem;
            font-weight: bold;
            color: hsl(${Math.max(0, Math.min(120 - 120 * resultFpsPercentage, 120))}deg 100% 31%);`, opts == null ? void 0 : opts.key);
      }
    }
    return result;
  };
}
function getMemoOptions(tableOptions, debugLevel, key, onChange) {
  return {
    debug: () => {
      var _tableOptions$debugAl;
      return (_tableOptions$debugAl = tableOptions == null ? void 0 : tableOptions.debugAll) != null ? _tableOptions$debugAl : tableOptions[debugLevel];
    },
    key: false,
    onChange
  };
}
function createCell(table2, row2, column, columnId) {
  const getRenderValue = () => {
    var _cell$getValue;
    return (_cell$getValue = cell2.getValue()) != null ? _cell$getValue : table2.options.renderFallbackValue;
  };
  const cell2 = {
    id: `${row2.id}_${column.id}`,
    row: row2,
    column,
    getValue: () => row2.getValue(columnId),
    renderValue: getRenderValue,
    getContext: memo$1(() => [table2, column, row2, cell2], (table22, column2, row22, cell22) => ({
      table: table22,
      column: column2,
      row: row22,
      cell: cell22,
      getValue: cell22.getValue,
      renderValue: cell22.renderValue
    }), getMemoOptions(table2.options, "debugCells"))
  };
  table2._features.forEach((feature) => {
    feature.createCell == null || feature.createCell(cell2, column, row2, table2);
  }, {});
  return cell2;
}
function createColumn(table2, columnDef, depth, parent) {
  var _ref, _resolvedColumnDef$id;
  const defaultColumn = table2._getDefaultColumnDef();
  const resolvedColumnDef = {
    ...defaultColumn,
    ...columnDef
  };
  const accessorKey = resolvedColumnDef.accessorKey;
  let id = (_ref = (_resolvedColumnDef$id = resolvedColumnDef.id) != null ? _resolvedColumnDef$id : accessorKey ? typeof String.prototype.replaceAll === "function" ? accessorKey.replaceAll(".", "_") : accessorKey.replace(/\./g, "_") : void 0) != null ? _ref : typeof resolvedColumnDef.header === "string" ? resolvedColumnDef.header : void 0;
  let accessorFn;
  if (resolvedColumnDef.accessorFn) {
    accessorFn = resolvedColumnDef.accessorFn;
  } else if (accessorKey) {
    if (accessorKey.includes(".")) {
      accessorFn = (originalRow) => {
        let result = originalRow;
        for (const key of accessorKey.split(".")) {
          var _result;
          result = (_result = result) == null ? void 0 : _result[key];
        }
        return result;
      };
    } else {
      accessorFn = (originalRow) => originalRow[resolvedColumnDef.accessorKey];
    }
  }
  if (!id) {
    throw new Error();
  }
  let column = {
    id: `${String(id)}`,
    accessorFn,
    parent,
    depth,
    columnDef: resolvedColumnDef,
    columns: [],
    getFlatColumns: memo$1(() => [true], () => {
      var _column$columns;
      return [column, ...(_column$columns = column.columns) == null ? void 0 : _column$columns.flatMap((d) => d.getFlatColumns())];
    }, getMemoOptions(table2.options, "debugColumns")),
    getLeafColumns: memo$1(() => [table2._getOrderColumnsFn()], (orderColumns2) => {
      var _column$columns2;
      if ((_column$columns2 = column.columns) != null && _column$columns2.length) {
        let leafColumns = column.columns.flatMap((column2) => column2.getLeafColumns());
        return orderColumns2(leafColumns);
      }
      return [column];
    }, getMemoOptions(table2.options, "debugColumns"))
  };
  for (const feature of table2._features) {
    feature.createColumn == null || feature.createColumn(column, table2);
  }
  return column;
}
const debug = "debugHeaders";
function createHeader(table2, column, options) {
  var _options$id;
  const id = (_options$id = options.id) != null ? _options$id : column.id;
  let header = {
    id,
    column,
    index: options.index,
    isPlaceholder: !!options.isPlaceholder,
    placeholderId: options.placeholderId,
    depth: options.depth,
    subHeaders: [],
    colSpan: 0,
    rowSpan: 0,
    headerGroup: null,
    getLeafHeaders: () => {
      const leafHeaders = [];
      const recurseHeader = (h) => {
        if (h.subHeaders && h.subHeaders.length) {
          h.subHeaders.map(recurseHeader);
        }
        leafHeaders.push(h);
      };
      recurseHeader(header);
      return leafHeaders;
    },
    getContext: () => ({
      table: table2,
      header,
      column
    })
  };
  table2._features.forEach((feature) => {
    feature.createHeader == null || feature.createHeader(header, table2);
  });
  return header;
}
const Headers = {
  createTable: (table2) => {
    table2.getHeaderGroups = memo$1(() => [table2.getAllColumns(), table2.getVisibleLeafColumns(), table2.getState().columnPinning.left, table2.getState().columnPinning.right], (allColumns, leafColumns, left, right) => {
      var _left$map$filter, _right$map$filter;
      const leftColumns = (_left$map$filter = left == null ? void 0 : left.map((columnId) => leafColumns.find((d) => d.id === columnId)).filter(Boolean)) != null ? _left$map$filter : [];
      const rightColumns = (_right$map$filter = right == null ? void 0 : right.map((columnId) => leafColumns.find((d) => d.id === columnId)).filter(Boolean)) != null ? _right$map$filter : [];
      const centerColumns = leafColumns.filter((column) => !(left != null && left.includes(column.id)) && !(right != null && right.includes(column.id)));
      const headerGroups = buildHeaderGroups(allColumns, [...leftColumns, ...centerColumns, ...rightColumns], table2);
      return headerGroups;
    }, getMemoOptions(table2.options, debug));
    table2.getCenterHeaderGroups = memo$1(() => [table2.getAllColumns(), table2.getVisibleLeafColumns(), table2.getState().columnPinning.left, table2.getState().columnPinning.right], (allColumns, leafColumns, left, right) => {
      leafColumns = leafColumns.filter((column) => !(left != null && left.includes(column.id)) && !(right != null && right.includes(column.id)));
      return buildHeaderGroups(allColumns, leafColumns, table2, "center");
    }, getMemoOptions(table2.options, debug));
    table2.getLeftHeaderGroups = memo$1(() => [table2.getAllColumns(), table2.getVisibleLeafColumns(), table2.getState().columnPinning.left], (allColumns, leafColumns, left) => {
      var _left$map$filter2;
      const orderedLeafColumns = (_left$map$filter2 = left == null ? void 0 : left.map((columnId) => leafColumns.find((d) => d.id === columnId)).filter(Boolean)) != null ? _left$map$filter2 : [];
      return buildHeaderGroups(allColumns, orderedLeafColumns, table2, "left");
    }, getMemoOptions(table2.options, debug));
    table2.getRightHeaderGroups = memo$1(() => [table2.getAllColumns(), table2.getVisibleLeafColumns(), table2.getState().columnPinning.right], (allColumns, leafColumns, right) => {
      var _right$map$filter2;
      const orderedLeafColumns = (_right$map$filter2 = right == null ? void 0 : right.map((columnId) => leafColumns.find((d) => d.id === columnId)).filter(Boolean)) != null ? _right$map$filter2 : [];
      return buildHeaderGroups(allColumns, orderedLeafColumns, table2, "right");
    }, getMemoOptions(table2.options, debug));
    table2.getFooterGroups = memo$1(() => [table2.getHeaderGroups()], (headerGroups) => {
      return [...headerGroups].reverse();
    }, getMemoOptions(table2.options, debug));
    table2.getLeftFooterGroups = memo$1(() => [table2.getLeftHeaderGroups()], (headerGroups) => {
      return [...headerGroups].reverse();
    }, getMemoOptions(table2.options, debug));
    table2.getCenterFooterGroups = memo$1(() => [table2.getCenterHeaderGroups()], (headerGroups) => {
      return [...headerGroups].reverse();
    }, getMemoOptions(table2.options, debug));
    table2.getRightFooterGroups = memo$1(() => [table2.getRightHeaderGroups()], (headerGroups) => {
      return [...headerGroups].reverse();
    }, getMemoOptions(table2.options, debug));
    table2.getFlatHeaders = memo$1(() => [table2.getHeaderGroups()], (headerGroups) => {
      return headerGroups.map((headerGroup) => {
        return headerGroup.headers;
      }).flat();
    }, getMemoOptions(table2.options, debug));
    table2.getLeftFlatHeaders = memo$1(() => [table2.getLeftHeaderGroups()], (left) => {
      return left.map((headerGroup) => {
        return headerGroup.headers;
      }).flat();
    }, getMemoOptions(table2.options, debug));
    table2.getCenterFlatHeaders = memo$1(() => [table2.getCenterHeaderGroups()], (left) => {
      return left.map((headerGroup) => {
        return headerGroup.headers;
      }).flat();
    }, getMemoOptions(table2.options, debug));
    table2.getRightFlatHeaders = memo$1(() => [table2.getRightHeaderGroups()], (left) => {
      return left.map((headerGroup) => {
        return headerGroup.headers;
      }).flat();
    }, getMemoOptions(table2.options, debug));
    table2.getCenterLeafHeaders = memo$1(() => [table2.getCenterFlatHeaders()], (flatHeaders) => {
      return flatHeaders.filter((header) => {
        var _header$subHeaders;
        return !((_header$subHeaders = header.subHeaders) != null && _header$subHeaders.length);
      });
    }, getMemoOptions(table2.options, debug));
    table2.getLeftLeafHeaders = memo$1(() => [table2.getLeftFlatHeaders()], (flatHeaders) => {
      return flatHeaders.filter((header) => {
        var _header$subHeaders2;
        return !((_header$subHeaders2 = header.subHeaders) != null && _header$subHeaders2.length);
      });
    }, getMemoOptions(table2.options, debug));
    table2.getRightLeafHeaders = memo$1(() => [table2.getRightFlatHeaders()], (flatHeaders) => {
      return flatHeaders.filter((header) => {
        var _header$subHeaders3;
        return !((_header$subHeaders3 = header.subHeaders) != null && _header$subHeaders3.length);
      });
    }, getMemoOptions(table2.options, debug));
    table2.getLeafHeaders = memo$1(() => [table2.getLeftHeaderGroups(), table2.getCenterHeaderGroups(), table2.getRightHeaderGroups()], (left, center, right) => {
      var _left$0$headers, _left$, _center$0$headers, _center$, _right$0$headers, _right$;
      return [...(_left$0$headers = (_left$ = left[0]) == null ? void 0 : _left$.headers) != null ? _left$0$headers : [], ...(_center$0$headers = (_center$ = center[0]) == null ? void 0 : _center$.headers) != null ? _center$0$headers : [], ...(_right$0$headers = (_right$ = right[0]) == null ? void 0 : _right$.headers) != null ? _right$0$headers : []].map((header) => {
        return header.getLeafHeaders();
      }).flat();
    }, getMemoOptions(table2.options, debug));
  }
};
function buildHeaderGroups(allColumns, columnsToGroup, table2, headerFamily) {
  var _headerGroups$0$heade, _headerGroups$;
  let maxDepth = 0;
  const findMaxDepth = function(columns, depth) {
    if (depth === void 0) {
      depth = 1;
    }
    maxDepth = Math.max(maxDepth, depth);
    columns.filter((column) => column.getIsVisible()).forEach((column) => {
      var _column$columns;
      if ((_column$columns = column.columns) != null && _column$columns.length) {
        findMaxDepth(column.columns, depth + 1);
      }
    }, 0);
  };
  findMaxDepth(allColumns);
  let headerGroups = [];
  const createHeaderGroup = (headersToGroup, depth) => {
    const headerGroup = {
      depth,
      id: [headerFamily, `${depth}`].filter(Boolean).join("_"),
      headers: []
    };
    const pendingParentHeaders = [];
    headersToGroup.forEach((headerToGroup) => {
      const latestPendingParentHeader = [...pendingParentHeaders].reverse()[0];
      const isLeafHeader = headerToGroup.column.depth === headerGroup.depth;
      let column;
      let isPlaceholder = false;
      if (isLeafHeader && headerToGroup.column.parent) {
        column = headerToGroup.column.parent;
      } else {
        column = headerToGroup.column;
        isPlaceholder = true;
      }
      if (latestPendingParentHeader && (latestPendingParentHeader == null ? void 0 : latestPendingParentHeader.column) === column) {
        latestPendingParentHeader.subHeaders.push(headerToGroup);
      } else {
        const header = createHeader(table2, column, {
          id: [headerFamily, depth, column.id, headerToGroup == null ? void 0 : headerToGroup.id].filter(Boolean).join("_"),
          isPlaceholder,
          placeholderId: isPlaceholder ? `${pendingParentHeaders.filter((d) => d.column === column).length}` : void 0,
          depth,
          index: pendingParentHeaders.length
        });
        header.subHeaders.push(headerToGroup);
        pendingParentHeaders.push(header);
      }
      headerGroup.headers.push(headerToGroup);
      headerToGroup.headerGroup = headerGroup;
    });
    headerGroups.push(headerGroup);
    if (depth > 0) {
      createHeaderGroup(pendingParentHeaders, depth - 1);
    }
  };
  const bottomHeaders = columnsToGroup.map((column, index) => createHeader(table2, column, {
    depth: maxDepth,
    index
  }));
  createHeaderGroup(bottomHeaders, maxDepth - 1);
  headerGroups.reverse();
  const recurseHeadersForSpans = (headers) => {
    const filteredHeaders = headers.filter((header) => header.column.getIsVisible());
    return filteredHeaders.map((header) => {
      let colSpan = 0;
      let rowSpan = 0;
      let childRowSpans = [0];
      if (header.subHeaders && header.subHeaders.length) {
        childRowSpans = [];
        recurseHeadersForSpans(header.subHeaders).forEach((_ref) => {
          let {
            colSpan: childColSpan,
            rowSpan: childRowSpan
          } = _ref;
          colSpan += childColSpan;
          childRowSpans.push(childRowSpan);
        });
      } else {
        colSpan = 1;
      }
      const minChildRowSpan = Math.min(...childRowSpans);
      rowSpan = rowSpan + minChildRowSpan;
      header.colSpan = colSpan;
      header.rowSpan = rowSpan;
      return {
        colSpan,
        rowSpan
      };
    });
  };
  recurseHeadersForSpans((_headerGroups$0$heade = (_headerGroups$ = headerGroups[0]) == null ? void 0 : _headerGroups$.headers) != null ? _headerGroups$0$heade : []);
  return headerGroups;
}
const createRow = (table2, id, original, rowIndex, depth, subRows, parentId) => {
  let row2 = {
    id,
    index: rowIndex,
    original,
    depth,
    parentId,
    _valuesCache: {},
    _uniqueValuesCache: {},
    getValue: (columnId) => {
      if (row2._valuesCache.hasOwnProperty(columnId)) {
        return row2._valuesCache[columnId];
      }
      const column = table2.getColumn(columnId);
      if (!(column != null && column.accessorFn)) {
        return void 0;
      }
      row2._valuesCache[columnId] = column.accessorFn(row2.original, rowIndex);
      return row2._valuesCache[columnId];
    },
    getUniqueValues: (columnId) => {
      if (row2._uniqueValuesCache.hasOwnProperty(columnId)) {
        return row2._uniqueValuesCache[columnId];
      }
      const column = table2.getColumn(columnId);
      if (!(column != null && column.accessorFn)) {
        return void 0;
      }
      if (!column.columnDef.getUniqueValues) {
        row2._uniqueValuesCache[columnId] = [row2.getValue(columnId)];
        return row2._uniqueValuesCache[columnId];
      }
      row2._uniqueValuesCache[columnId] = column.columnDef.getUniqueValues(row2.original, rowIndex);
      return row2._uniqueValuesCache[columnId];
    },
    renderValue: (columnId) => {
      var _row$getValue;
      return (_row$getValue = row2.getValue(columnId)) != null ? _row$getValue : table2.options.renderFallbackValue;
    },
    subRows: [],
    getLeafRows: () => flattenBy(row2.subRows, (d) => d.subRows),
    getParentRow: () => row2.parentId ? table2.getRow(row2.parentId, true) : void 0,
    getParentRows: () => {
      let parentRows = [];
      let currentRow = row2;
      while (true) {
        const parentRow = currentRow.getParentRow();
        if (!parentRow) break;
        parentRows.push(parentRow);
        currentRow = parentRow;
      }
      return parentRows.reverse();
    },
    getAllCells: memo$1(() => [table2.getAllLeafColumns()], (leafColumns) => {
      return leafColumns.map((column) => {
        return createCell(table2, row2, column, column.id);
      });
    }, getMemoOptions(table2.options, "debugRows")),
    _getAllCellsByColumnId: memo$1(() => [row2.getAllCells()], (allCells) => {
      return allCells.reduce((acc, cell2) => {
        acc[cell2.column.id] = cell2;
        return acc;
      }, {});
    }, getMemoOptions(table2.options, "debugRows"))
  };
  for (let i = 0; i < table2._features.length; i++) {
    const feature = table2._features[i];
    feature == null || feature.createRow == null || feature.createRow(row2, table2);
  }
  return row2;
};
const ColumnFaceting = {
  createColumn: (column, table2) => {
    column._getFacetedRowModel = table2.options.getFacetedRowModel && table2.options.getFacetedRowModel(table2, column.id);
    column.getFacetedRowModel = () => {
      if (!column._getFacetedRowModel) {
        return table2.getPreFilteredRowModel();
      }
      return column._getFacetedRowModel();
    };
    column._getFacetedUniqueValues = table2.options.getFacetedUniqueValues && table2.options.getFacetedUniqueValues(table2, column.id);
    column.getFacetedUniqueValues = () => {
      if (!column._getFacetedUniqueValues) {
        return /* @__PURE__ */ new Map();
      }
      return column._getFacetedUniqueValues();
    };
    column._getFacetedMinMaxValues = table2.options.getFacetedMinMaxValues && table2.options.getFacetedMinMaxValues(table2, column.id);
    column.getFacetedMinMaxValues = () => {
      if (!column._getFacetedMinMaxValues) {
        return void 0;
      }
      return column._getFacetedMinMaxValues();
    };
  }
};
const includesString = (row2, columnId, filterValue) => {
  var _filterValue$toString, _row$getValue;
  const search = filterValue == null || (_filterValue$toString = filterValue.toString()) == null ? void 0 : _filterValue$toString.toLowerCase();
  return Boolean((_row$getValue = row2.getValue(columnId)) == null || (_row$getValue = _row$getValue.toString()) == null || (_row$getValue = _row$getValue.toLowerCase()) == null ? void 0 : _row$getValue.includes(search));
};
includesString.autoRemove = (val) => testFalsey(val);
const includesStringSensitive = (row2, columnId, filterValue) => {
  var _row$getValue2;
  return Boolean((_row$getValue2 = row2.getValue(columnId)) == null || (_row$getValue2 = _row$getValue2.toString()) == null ? void 0 : _row$getValue2.includes(filterValue));
};
includesStringSensitive.autoRemove = (val) => testFalsey(val);
const equalsString = (row2, columnId, filterValue) => {
  var _row$getValue3;
  return ((_row$getValue3 = row2.getValue(columnId)) == null || (_row$getValue3 = _row$getValue3.toString()) == null ? void 0 : _row$getValue3.toLowerCase()) === (filterValue == null ? void 0 : filterValue.toLowerCase());
};
equalsString.autoRemove = (val) => testFalsey(val);
const arrIncludes = (row2, columnId, filterValue) => {
  var _row$getValue4;
  return (_row$getValue4 = row2.getValue(columnId)) == null ? void 0 : _row$getValue4.includes(filterValue);
};
arrIncludes.autoRemove = (val) => testFalsey(val);
const arrIncludesAll = (row2, columnId, filterValue) => {
  return !filterValue.some((val) => {
    var _row$getValue5;
    return !((_row$getValue5 = row2.getValue(columnId)) != null && _row$getValue5.includes(val));
  });
};
arrIncludesAll.autoRemove = (val) => testFalsey(val) || !(val != null && val.length);
const arrIncludesSome = (row2, columnId, filterValue) => {
  return filterValue.some((val) => {
    var _row$getValue6;
    return (_row$getValue6 = row2.getValue(columnId)) == null ? void 0 : _row$getValue6.includes(val);
  });
};
arrIncludesSome.autoRemove = (val) => testFalsey(val) || !(val != null && val.length);
const equals = (row2, columnId, filterValue) => {
  return row2.getValue(columnId) === filterValue;
};
equals.autoRemove = (val) => testFalsey(val);
const weakEquals = (row2, columnId, filterValue) => {
  return row2.getValue(columnId) == filterValue;
};
weakEquals.autoRemove = (val) => testFalsey(val);
const inNumberRange = (row2, columnId, filterValue) => {
  let [min2, max2] = filterValue;
  const rowValue = row2.getValue(columnId);
  return rowValue >= min2 && rowValue <= max2;
};
inNumberRange.resolveFilterValue = (val) => {
  let [unsafeMin, unsafeMax] = val;
  let parsedMin = typeof unsafeMin !== "number" ? parseFloat(unsafeMin) : unsafeMin;
  let parsedMax = typeof unsafeMax !== "number" ? parseFloat(unsafeMax) : unsafeMax;
  let min2 = unsafeMin === null || Number.isNaN(parsedMin) ? -Infinity : parsedMin;
  let max2 = unsafeMax === null || Number.isNaN(parsedMax) ? Infinity : parsedMax;
  if (min2 > max2) {
    const temp = min2;
    min2 = max2;
    max2 = temp;
  }
  return [min2, max2];
};
inNumberRange.autoRemove = (val) => testFalsey(val) || testFalsey(val[0]) && testFalsey(val[1]);
const filterFns = {
  includesString,
  includesStringSensitive,
  equalsString,
  arrIncludes,
  arrIncludesAll,
  arrIncludesSome,
  equals,
  weakEquals,
  inNumberRange
};
function testFalsey(val) {
  return val === void 0 || val === null || val === "";
}
const ColumnFiltering = {
  getDefaultColumnDef: () => {
    return {
      filterFn: "auto"
    };
  },
  getInitialState: (state) => {
    return {
      columnFilters: [],
      ...state
    };
  },
  getDefaultOptions: (table2) => {
    return {
      onColumnFiltersChange: makeStateUpdater("columnFilters", table2),
      filterFromLeafRows: false,
      maxLeafRowFilterDepth: 100
    };
  },
  createColumn: (column, table2) => {
    column.getAutoFilterFn = () => {
      const firstRow = table2.getCoreRowModel().flatRows[0];
      const value = firstRow == null ? void 0 : firstRow.getValue(column.id);
      if (typeof value === "string") {
        return filterFns.includesString;
      }
      if (typeof value === "number") {
        return filterFns.inNumberRange;
      }
      if (typeof value === "boolean") {
        return filterFns.equals;
      }
      if (value !== null && typeof value === "object") {
        return filterFns.equals;
      }
      if (Array.isArray(value)) {
        return filterFns.arrIncludes;
      }
      return filterFns.weakEquals;
    };
    column.getFilterFn = () => {
      var _table$options$filter, _table$options$filter2;
      return isFunction(column.columnDef.filterFn) ? column.columnDef.filterFn : column.columnDef.filterFn === "auto" ? column.getAutoFilterFn() : (
        // @ts-ignore
        (_table$options$filter = (_table$options$filter2 = table2.options.filterFns) == null ? void 0 : _table$options$filter2[column.columnDef.filterFn]) != null ? _table$options$filter : filterFns[column.columnDef.filterFn]
      );
    };
    column.getCanFilter = () => {
      var _column$columnDef$ena, _table$options$enable, _table$options$enable2;
      return ((_column$columnDef$ena = column.columnDef.enableColumnFilter) != null ? _column$columnDef$ena : true) && ((_table$options$enable = table2.options.enableColumnFilters) != null ? _table$options$enable : true) && ((_table$options$enable2 = table2.options.enableFilters) != null ? _table$options$enable2 : true) && !!column.accessorFn;
    };
    column.getIsFiltered = () => column.getFilterIndex() > -1;
    column.getFilterValue = () => {
      var _table$getState$colum;
      return (_table$getState$colum = table2.getState().columnFilters) == null || (_table$getState$colum = _table$getState$colum.find((d) => d.id === column.id)) == null ? void 0 : _table$getState$colum.value;
    };
    column.getFilterIndex = () => {
      var _table$getState$colum2, _table$getState$colum3;
      return (_table$getState$colum2 = (_table$getState$colum3 = table2.getState().columnFilters) == null ? void 0 : _table$getState$colum3.findIndex((d) => d.id === column.id)) != null ? _table$getState$colum2 : -1;
    };
    column.setFilterValue = (value) => {
      table2.setColumnFilters((old) => {
        const filterFn = column.getFilterFn();
        const previousFilter = old == null ? void 0 : old.find((d) => d.id === column.id);
        const newFilter = functionalUpdate(value, previousFilter ? previousFilter.value : void 0);
        if (shouldAutoRemoveFilter(filterFn, newFilter, column)) {
          var _old$filter;
          return (_old$filter = old == null ? void 0 : old.filter((d) => d.id !== column.id)) != null ? _old$filter : [];
        }
        const newFilterObj = {
          id: column.id,
          value: newFilter
        };
        if (previousFilter) {
          var _old$map;
          return (_old$map = old == null ? void 0 : old.map((d) => {
            if (d.id === column.id) {
              return newFilterObj;
            }
            return d;
          })) != null ? _old$map : [];
        }
        if (old != null && old.length) {
          return [...old, newFilterObj];
        }
        return [newFilterObj];
      });
    };
  },
  createRow: (row2, _table) => {
    row2.columnFilters = {};
    row2.columnFiltersMeta = {};
  },
  createTable: (table2) => {
    table2.setColumnFilters = (updater) => {
      const leafColumns = table2.getAllLeafColumns();
      const updateFn = (old) => {
        var _functionalUpdate;
        return (_functionalUpdate = functionalUpdate(updater, old)) == null ? void 0 : _functionalUpdate.filter((filter) => {
          const column = leafColumns.find((d) => d.id === filter.id);
          if (column) {
            const filterFn = column.getFilterFn();
            if (shouldAutoRemoveFilter(filterFn, filter.value, column)) {
              return false;
            }
          }
          return true;
        });
      };
      table2.options.onColumnFiltersChange == null || table2.options.onColumnFiltersChange(updateFn);
    };
    table2.resetColumnFilters = (defaultState) => {
      var _table$initialState$c, _table$initialState;
      table2.setColumnFilters(defaultState ? [] : (_table$initialState$c = (_table$initialState = table2.initialState) == null ? void 0 : _table$initialState.columnFilters) != null ? _table$initialState$c : []);
    };
    table2.getPreFilteredRowModel = () => table2.getCoreRowModel();
    table2.getFilteredRowModel = () => {
      if (!table2._getFilteredRowModel && table2.options.getFilteredRowModel) {
        table2._getFilteredRowModel = table2.options.getFilteredRowModel(table2);
      }
      if (table2.options.manualFiltering || !table2._getFilteredRowModel) {
        return table2.getPreFilteredRowModel();
      }
      return table2._getFilteredRowModel();
    };
  }
};
function shouldAutoRemoveFilter(filterFn, value, column) {
  return (filterFn && filterFn.autoRemove ? filterFn.autoRemove(value, column) : false) || typeof value === "undefined" || typeof value === "string" && !value;
}
const sum = (columnId, _leafRows, childRows) => {
  return childRows.reduce((sum2, next) => {
    const nextValue = next.getValue(columnId);
    return sum2 + (typeof nextValue === "number" ? nextValue : 0);
  }, 0);
};
const min = (columnId, _leafRows, childRows) => {
  let min2;
  childRows.forEach((row2) => {
    const value = row2.getValue(columnId);
    if (value != null && (min2 > value || min2 === void 0 && value >= value)) {
      min2 = value;
    }
  });
  return min2;
};
const max = (columnId, _leafRows, childRows) => {
  let max2;
  childRows.forEach((row2) => {
    const value = row2.getValue(columnId);
    if (value != null && (max2 < value || max2 === void 0 && value >= value)) {
      max2 = value;
    }
  });
  return max2;
};
const extent = (columnId, _leafRows, childRows) => {
  let min2;
  let max2;
  childRows.forEach((row2) => {
    const value = row2.getValue(columnId);
    if (value != null) {
      if (min2 === void 0) {
        if (value >= value) min2 = max2 = value;
      } else {
        if (min2 > value) min2 = value;
        if (max2 < value) max2 = value;
      }
    }
  });
  return [min2, max2];
};
const mean = (columnId, leafRows) => {
  let count2 = 0;
  let sum2 = 0;
  leafRows.forEach((row2) => {
    let value = row2.getValue(columnId);
    if (value != null && (value = +value) >= value) {
      ++count2, sum2 += value;
    }
  });
  if (count2) return sum2 / count2;
  return;
};
const median = (columnId, leafRows) => {
  if (!leafRows.length) {
    return;
  }
  const values = leafRows.map((row2) => row2.getValue(columnId));
  if (!isNumberArray(values)) {
    return;
  }
  if (values.length === 1) {
    return values[0];
  }
  const mid = Math.floor(values.length / 2);
  const nums = values.sort((a, b) => a - b);
  return values.length % 2 !== 0 ? nums[mid] : (nums[mid - 1] + nums[mid]) / 2;
};
const unique = (columnId, leafRows) => {
  return Array.from(new Set(leafRows.map((d) => d.getValue(columnId))).values());
};
const uniqueCount = (columnId, leafRows) => {
  return new Set(leafRows.map((d) => d.getValue(columnId))).size;
};
const count = (_columnId, leafRows) => {
  return leafRows.length;
};
const aggregationFns = {
  sum,
  min,
  max,
  extent,
  mean,
  median,
  unique,
  uniqueCount,
  count
};
const ColumnGrouping = {
  getDefaultColumnDef: () => {
    return {
      aggregatedCell: (props) => {
        var _toString, _props$getValue;
        return (_toString = (_props$getValue = props.getValue()) == null || _props$getValue.toString == null ? void 0 : _props$getValue.toString()) != null ? _toString : null;
      },
      aggregationFn: "auto"
    };
  },
  getInitialState: (state) => {
    return {
      grouping: [],
      ...state
    };
  },
  getDefaultOptions: (table2) => {
    return {
      onGroupingChange: makeStateUpdater("grouping", table2),
      groupedColumnMode: "reorder"
    };
  },
  createColumn: (column, table2) => {
    column.toggleGrouping = () => {
      table2.setGrouping((old) => {
        if (old != null && old.includes(column.id)) {
          return old.filter((d) => d !== column.id);
        }
        return [...old != null ? old : [], column.id];
      });
    };
    column.getCanGroup = () => {
      var _column$columnDef$ena, _table$options$enable;
      return ((_column$columnDef$ena = column.columnDef.enableGrouping) != null ? _column$columnDef$ena : true) && ((_table$options$enable = table2.options.enableGrouping) != null ? _table$options$enable : true) && (!!column.accessorFn || !!column.columnDef.getGroupingValue);
    };
    column.getIsGrouped = () => {
      var _table$getState$group;
      return (_table$getState$group = table2.getState().grouping) == null ? void 0 : _table$getState$group.includes(column.id);
    };
    column.getGroupedIndex = () => {
      var _table$getState$group2;
      return (_table$getState$group2 = table2.getState().grouping) == null ? void 0 : _table$getState$group2.indexOf(column.id);
    };
    column.getToggleGroupingHandler = () => {
      const canGroup = column.getCanGroup();
      return () => {
        if (!canGroup) return;
        column.toggleGrouping();
      };
    };
    column.getAutoAggregationFn = () => {
      const firstRow = table2.getCoreRowModel().flatRows[0];
      const value = firstRow == null ? void 0 : firstRow.getValue(column.id);
      if (typeof value === "number") {
        return aggregationFns.sum;
      }
      if (Object.prototype.toString.call(value) === "[object Date]") {
        return aggregationFns.extent;
      }
    };
    column.getAggregationFn = () => {
      var _table$options$aggreg, _table$options$aggreg2;
      if (!column) {
        throw new Error();
      }
      return isFunction(column.columnDef.aggregationFn) ? column.columnDef.aggregationFn : column.columnDef.aggregationFn === "auto" ? column.getAutoAggregationFn() : (_table$options$aggreg = (_table$options$aggreg2 = table2.options.aggregationFns) == null ? void 0 : _table$options$aggreg2[column.columnDef.aggregationFn]) != null ? _table$options$aggreg : aggregationFns[column.columnDef.aggregationFn];
    };
  },
  createTable: (table2) => {
    table2.setGrouping = (updater) => table2.options.onGroupingChange == null ? void 0 : table2.options.onGroupingChange(updater);
    table2.resetGrouping = (defaultState) => {
      var _table$initialState$g, _table$initialState;
      table2.setGrouping(defaultState ? [] : (_table$initialState$g = (_table$initialState = table2.initialState) == null ? void 0 : _table$initialState.grouping) != null ? _table$initialState$g : []);
    };
    table2.getPreGroupedRowModel = () => table2.getFilteredRowModel();
    table2.getGroupedRowModel = () => {
      if (!table2._getGroupedRowModel && table2.options.getGroupedRowModel) {
        table2._getGroupedRowModel = table2.options.getGroupedRowModel(table2);
      }
      if (table2.options.manualGrouping || !table2._getGroupedRowModel) {
        return table2.getPreGroupedRowModel();
      }
      return table2._getGroupedRowModel();
    };
  },
  createRow: (row2, table2) => {
    row2.getIsGrouped = () => !!row2.groupingColumnId;
    row2.getGroupingValue = (columnId) => {
      if (row2._groupingValuesCache.hasOwnProperty(columnId)) {
        return row2._groupingValuesCache[columnId];
      }
      const column = table2.getColumn(columnId);
      if (!(column != null && column.columnDef.getGroupingValue)) {
        return row2.getValue(columnId);
      }
      row2._groupingValuesCache[columnId] = column.columnDef.getGroupingValue(row2.original);
      return row2._groupingValuesCache[columnId];
    };
    row2._groupingValuesCache = {};
  },
  createCell: (cell2, column, row2, table2) => {
    cell2.getIsGrouped = () => column.getIsGrouped() && column.id === row2.groupingColumnId;
    cell2.getIsPlaceholder = () => !cell2.getIsGrouped() && column.getIsGrouped();
    cell2.getIsAggregated = () => {
      var _row$subRows;
      return !cell2.getIsGrouped() && !cell2.getIsPlaceholder() && !!((_row$subRows = row2.subRows) != null && _row$subRows.length);
    };
  }
};
function orderColumns(leafColumns, grouping, groupedColumnMode) {
  if (!(grouping != null && grouping.length) || !groupedColumnMode) {
    return leafColumns;
  }
  const nonGroupingColumns = leafColumns.filter((col) => !grouping.includes(col.id));
  if (groupedColumnMode === "remove") {
    return nonGroupingColumns;
  }
  const groupingColumns = grouping.map((g) => leafColumns.find((col) => col.id === g)).filter(Boolean);
  return [...groupingColumns, ...nonGroupingColumns];
}
const ColumnOrdering = {
  getInitialState: (state) => {
    return {
      columnOrder: [],
      ...state
    };
  },
  getDefaultOptions: (table2) => {
    return {
      onColumnOrderChange: makeStateUpdater("columnOrder", table2)
    };
  },
  createColumn: (column, table2) => {
    column.getIndex = memo$1((position) => [_getVisibleLeafColumns(table2, position)], (columns) => columns.findIndex((d) => d.id === column.id), getMemoOptions(table2.options, "debugColumns"));
    column.getIsFirstColumn = (position) => {
      var _columns$;
      const columns = _getVisibleLeafColumns(table2, position);
      return ((_columns$ = columns[0]) == null ? void 0 : _columns$.id) === column.id;
    };
    column.getIsLastColumn = (position) => {
      var _columns;
      const columns = _getVisibleLeafColumns(table2, position);
      return ((_columns = columns[columns.length - 1]) == null ? void 0 : _columns.id) === column.id;
    };
  },
  createTable: (table2) => {
    table2.setColumnOrder = (updater) => table2.options.onColumnOrderChange == null ? void 0 : table2.options.onColumnOrderChange(updater);
    table2.resetColumnOrder = (defaultState) => {
      var _table$initialState$c;
      table2.setColumnOrder(defaultState ? [] : (_table$initialState$c = table2.initialState.columnOrder) != null ? _table$initialState$c : []);
    };
    table2._getOrderColumnsFn = memo$1(() => [table2.getState().columnOrder, table2.getState().grouping, table2.options.groupedColumnMode], (columnOrder, grouping, groupedColumnMode) => (columns) => {
      let orderedColumns = [];
      if (!(columnOrder != null && columnOrder.length)) {
        orderedColumns = columns;
      } else {
        const columnOrderCopy = [...columnOrder];
        const columnsCopy = [...columns];
        while (columnsCopy.length && columnOrderCopy.length) {
          const targetColumnId = columnOrderCopy.shift();
          const foundIndex = columnsCopy.findIndex((d) => d.id === targetColumnId);
          if (foundIndex > -1) {
            orderedColumns.push(columnsCopy.splice(foundIndex, 1)[0]);
          }
        }
        orderedColumns = [...orderedColumns, ...columnsCopy];
      }
      return orderColumns(orderedColumns, grouping, groupedColumnMode);
    }, getMemoOptions(table2.options, "debugTable"));
  }
};
const getDefaultColumnPinningState = () => ({
  left: [],
  right: []
});
const ColumnPinning = {
  getInitialState: (state) => {
    return {
      columnPinning: getDefaultColumnPinningState(),
      ...state
    };
  },
  getDefaultOptions: (table2) => {
    return {
      onColumnPinningChange: makeStateUpdater("columnPinning", table2)
    };
  },
  createColumn: (column, table2) => {
    column.pin = (position) => {
      const columnIds = column.getLeafColumns().map((d) => d.id).filter(Boolean);
      table2.setColumnPinning((old) => {
        var _old$left3, _old$right3;
        if (position === "right") {
          var _old$left, _old$right;
          return {
            left: ((_old$left = old == null ? void 0 : old.left) != null ? _old$left : []).filter((d) => !(columnIds != null && columnIds.includes(d))),
            right: [...((_old$right = old == null ? void 0 : old.right) != null ? _old$right : []).filter((d) => !(columnIds != null && columnIds.includes(d))), ...columnIds]
          };
        }
        if (position === "left") {
          var _old$left2, _old$right2;
          return {
            left: [...((_old$left2 = old == null ? void 0 : old.left) != null ? _old$left2 : []).filter((d) => !(columnIds != null && columnIds.includes(d))), ...columnIds],
            right: ((_old$right2 = old == null ? void 0 : old.right) != null ? _old$right2 : []).filter((d) => !(columnIds != null && columnIds.includes(d)))
          };
        }
        return {
          left: ((_old$left3 = old == null ? void 0 : old.left) != null ? _old$left3 : []).filter((d) => !(columnIds != null && columnIds.includes(d))),
          right: ((_old$right3 = old == null ? void 0 : old.right) != null ? _old$right3 : []).filter((d) => !(columnIds != null && columnIds.includes(d)))
        };
      });
    };
    column.getCanPin = () => {
      const leafColumns = column.getLeafColumns();
      return leafColumns.some((d) => {
        var _d$columnDef$enablePi, _ref, _table$options$enable;
        return ((_d$columnDef$enablePi = d.columnDef.enablePinning) != null ? _d$columnDef$enablePi : true) && ((_ref = (_table$options$enable = table2.options.enableColumnPinning) != null ? _table$options$enable : table2.options.enablePinning) != null ? _ref : true);
      });
    };
    column.getIsPinned = () => {
      const leafColumnIds = column.getLeafColumns().map((d) => d.id);
      const {
        left,
        right
      } = table2.getState().columnPinning;
      const isLeft = leafColumnIds.some((d) => left == null ? void 0 : left.includes(d));
      const isRight = leafColumnIds.some((d) => right == null ? void 0 : right.includes(d));
      return isLeft ? "left" : isRight ? "right" : false;
    };
    column.getPinnedIndex = () => {
      var _table$getState$colum, _table$getState$colum2;
      const position = column.getIsPinned();
      return position ? (_table$getState$colum = (_table$getState$colum2 = table2.getState().columnPinning) == null || (_table$getState$colum2 = _table$getState$colum2[position]) == null ? void 0 : _table$getState$colum2.indexOf(column.id)) != null ? _table$getState$colum : -1 : 0;
    };
  },
  createRow: (row2, table2) => {
    row2.getCenterVisibleCells = memo$1(() => [row2._getAllVisibleCells(), table2.getState().columnPinning.left, table2.getState().columnPinning.right], (allCells, left, right) => {
      const leftAndRight = [...left != null ? left : [], ...right != null ? right : []];
      return allCells.filter((d) => !leftAndRight.includes(d.column.id));
    }, getMemoOptions(table2.options, "debugRows"));
    row2.getLeftVisibleCells = memo$1(() => [row2._getAllVisibleCells(), table2.getState().columnPinning.left], (allCells, left) => {
      const cells = (left != null ? left : []).map((columnId) => allCells.find((cell2) => cell2.column.id === columnId)).filter(Boolean).map((d) => ({
        ...d,
        position: "left"
      }));
      return cells;
    }, getMemoOptions(table2.options, "debugRows"));
    row2.getRightVisibleCells = memo$1(() => [row2._getAllVisibleCells(), table2.getState().columnPinning.right], (allCells, right) => {
      const cells = (right != null ? right : []).map((columnId) => allCells.find((cell2) => cell2.column.id === columnId)).filter(Boolean).map((d) => ({
        ...d,
        position: "right"
      }));
      return cells;
    }, getMemoOptions(table2.options, "debugRows"));
  },
  createTable: (table2) => {
    table2.setColumnPinning = (updater) => table2.options.onColumnPinningChange == null ? void 0 : table2.options.onColumnPinningChange(updater);
    table2.resetColumnPinning = (defaultState) => {
      var _table$initialState$c, _table$initialState;
      return table2.setColumnPinning(defaultState ? getDefaultColumnPinningState() : (_table$initialState$c = (_table$initialState = table2.initialState) == null ? void 0 : _table$initialState.columnPinning) != null ? _table$initialState$c : getDefaultColumnPinningState());
    };
    table2.getIsSomeColumnsPinned = (position) => {
      var _pinningState$positio;
      const pinningState = table2.getState().columnPinning;
      if (!position) {
        var _pinningState$left, _pinningState$right;
        return Boolean(((_pinningState$left = pinningState.left) == null ? void 0 : _pinningState$left.length) || ((_pinningState$right = pinningState.right) == null ? void 0 : _pinningState$right.length));
      }
      return Boolean((_pinningState$positio = pinningState[position]) == null ? void 0 : _pinningState$positio.length);
    };
    table2.getLeftLeafColumns = memo$1(() => [table2.getAllLeafColumns(), table2.getState().columnPinning.left], (allColumns, left) => {
      return (left != null ? left : []).map((columnId) => allColumns.find((column) => column.id === columnId)).filter(Boolean);
    }, getMemoOptions(table2.options, "debugColumns"));
    table2.getRightLeafColumns = memo$1(() => [table2.getAllLeafColumns(), table2.getState().columnPinning.right], (allColumns, right) => {
      return (right != null ? right : []).map((columnId) => allColumns.find((column) => column.id === columnId)).filter(Boolean);
    }, getMemoOptions(table2.options, "debugColumns"));
    table2.getCenterLeafColumns = memo$1(() => [table2.getAllLeafColumns(), table2.getState().columnPinning.left, table2.getState().columnPinning.right], (allColumns, left, right) => {
      const leftAndRight = [...left != null ? left : [], ...right != null ? right : []];
      return allColumns.filter((d) => !leftAndRight.includes(d.id));
    }, getMemoOptions(table2.options, "debugColumns"));
  }
};
function safelyAccessDocument(_document) {
  return _document || (typeof document !== "undefined" ? document : null);
}
const defaultColumnSizing = {
  size: 150,
  minSize: 20,
  maxSize: Number.MAX_SAFE_INTEGER
};
const getDefaultColumnSizingInfoState = () => ({
  startOffset: null,
  startSize: null,
  deltaOffset: null,
  deltaPercentage: null,
  isResizingColumn: false,
  columnSizingStart: []
});
const ColumnSizing = {
  getDefaultColumnDef: () => {
    return defaultColumnSizing;
  },
  getInitialState: (state) => {
    return {
      columnSizing: {},
      columnSizingInfo: getDefaultColumnSizingInfoState(),
      ...state
    };
  },
  getDefaultOptions: (table2) => {
    return {
      columnResizeMode: "onEnd",
      columnResizeDirection: "ltr",
      onColumnSizingChange: makeStateUpdater("columnSizing", table2),
      onColumnSizingInfoChange: makeStateUpdater("columnSizingInfo", table2)
    };
  },
  createColumn: (column, table2) => {
    column.getSize = () => {
      var _column$columnDef$min, _ref, _column$columnDef$max;
      const columnSize = table2.getState().columnSizing[column.id];
      return Math.min(Math.max((_column$columnDef$min = column.columnDef.minSize) != null ? _column$columnDef$min : defaultColumnSizing.minSize, (_ref = columnSize != null ? columnSize : column.columnDef.size) != null ? _ref : defaultColumnSizing.size), (_column$columnDef$max = column.columnDef.maxSize) != null ? _column$columnDef$max : defaultColumnSizing.maxSize);
    };
    column.getStart = memo$1((position) => [position, _getVisibleLeafColumns(table2, position), table2.getState().columnSizing], (position, columns) => columns.slice(0, column.getIndex(position)).reduce((sum2, column2) => sum2 + column2.getSize(), 0), getMemoOptions(table2.options, "debugColumns"));
    column.getAfter = memo$1((position) => [position, _getVisibleLeafColumns(table2, position), table2.getState().columnSizing], (position, columns) => columns.slice(column.getIndex(position) + 1).reduce((sum2, column2) => sum2 + column2.getSize(), 0), getMemoOptions(table2.options, "debugColumns"));
    column.resetSize = () => {
      table2.setColumnSizing((_ref2) => {
        let {
          [column.id]: _,
          ...rest
        } = _ref2;
        return rest;
      });
    };
    column.getCanResize = () => {
      var _column$columnDef$ena, _table$options$enable;
      return ((_column$columnDef$ena = column.columnDef.enableResizing) != null ? _column$columnDef$ena : true) && ((_table$options$enable = table2.options.enableColumnResizing) != null ? _table$options$enable : true);
    };
    column.getIsResizing = () => {
      return table2.getState().columnSizingInfo.isResizingColumn === column.id;
    };
  },
  createHeader: (header, table2) => {
    header.getSize = () => {
      let sum2 = 0;
      const recurse = (header2) => {
        if (header2.subHeaders.length) {
          header2.subHeaders.forEach(recurse);
        } else {
          var _header$column$getSiz;
          sum2 += (_header$column$getSiz = header2.column.getSize()) != null ? _header$column$getSiz : 0;
        }
      };
      recurse(header);
      return sum2;
    };
    header.getStart = () => {
      if (header.index > 0) {
        const prevSiblingHeader = header.headerGroup.headers[header.index - 1];
        return prevSiblingHeader.getStart() + prevSiblingHeader.getSize();
      }
      return 0;
    };
    header.getResizeHandler = (_contextDocument) => {
      const column = table2.getColumn(header.column.id);
      const canResize = column == null ? void 0 : column.getCanResize();
      return (e) => {
        if (!column || !canResize) {
          return;
        }
        e.persist == null || e.persist();
        if (isTouchStartEvent(e)) {
          if (e.touches && e.touches.length > 1) {
            return;
          }
        }
        const startSize = header.getSize();
        const columnSizingStart = header ? header.getLeafHeaders().map((d) => [d.column.id, d.column.getSize()]) : [[column.id, column.getSize()]];
        const clientX = isTouchStartEvent(e) ? Math.round(e.touches[0].clientX) : e.clientX;
        const newColumnSizing = {};
        const updateOffset = (eventType, clientXPos) => {
          if (typeof clientXPos !== "number") {
            return;
          }
          table2.setColumnSizingInfo((old) => {
            var _old$startOffset, _old$startSize;
            const deltaDirection = table2.options.columnResizeDirection === "rtl" ? -1 : 1;
            const deltaOffset = (clientXPos - ((_old$startOffset = old == null ? void 0 : old.startOffset) != null ? _old$startOffset : 0)) * deltaDirection;
            const deltaPercentage = Math.max(deltaOffset / ((_old$startSize = old == null ? void 0 : old.startSize) != null ? _old$startSize : 0), -0.999999);
            old.columnSizingStart.forEach((_ref3) => {
              let [columnId, headerSize] = _ref3;
              newColumnSizing[columnId] = Math.round(Math.max(headerSize + headerSize * deltaPercentage, 0) * 100) / 100;
            });
            return {
              ...old,
              deltaOffset,
              deltaPercentage
            };
          });
          if (table2.options.columnResizeMode === "onChange" || eventType === "end") {
            table2.setColumnSizing((old) => ({
              ...old,
              ...newColumnSizing
            }));
          }
        };
        const onMove = (clientXPos) => updateOffset("move", clientXPos);
        const onEnd = (clientXPos) => {
          updateOffset("end", clientXPos);
          table2.setColumnSizingInfo((old) => ({
            ...old,
            isResizingColumn: false,
            startOffset: null,
            startSize: null,
            deltaOffset: null,
            deltaPercentage: null,
            columnSizingStart: []
          }));
        };
        const contextDocument = safelyAccessDocument(_contextDocument);
        const mouseEvents = {
          moveHandler: (e2) => onMove(e2.clientX),
          upHandler: (e2) => {
            contextDocument == null || contextDocument.removeEventListener("mousemove", mouseEvents.moveHandler);
            contextDocument == null || contextDocument.removeEventListener("mouseup", mouseEvents.upHandler);
            onEnd(e2.clientX);
          }
        };
        const touchEvents = {
          moveHandler: (e2) => {
            if (e2.cancelable) {
              e2.preventDefault();
              e2.stopPropagation();
            }
            onMove(e2.touches[0].clientX);
            return false;
          },
          upHandler: (e2) => {
            var _e$touches$;
            contextDocument == null || contextDocument.removeEventListener("touchmove", touchEvents.moveHandler);
            contextDocument == null || contextDocument.removeEventListener("touchend", touchEvents.upHandler);
            if (e2.cancelable) {
              e2.preventDefault();
              e2.stopPropagation();
            }
            onEnd((_e$touches$ = e2.touches[0]) == null ? void 0 : _e$touches$.clientX);
          }
        };
        const passiveIfSupported = passiveEventSupported() ? {
          passive: false
        } : false;
        if (isTouchStartEvent(e)) {
          contextDocument == null || contextDocument.addEventListener("touchmove", touchEvents.moveHandler, passiveIfSupported);
          contextDocument == null || contextDocument.addEventListener("touchend", touchEvents.upHandler, passiveIfSupported);
        } else {
          contextDocument == null || contextDocument.addEventListener("mousemove", mouseEvents.moveHandler, passiveIfSupported);
          contextDocument == null || contextDocument.addEventListener("mouseup", mouseEvents.upHandler, passiveIfSupported);
        }
        table2.setColumnSizingInfo((old) => ({
          ...old,
          startOffset: clientX,
          startSize,
          deltaOffset: 0,
          deltaPercentage: 0,
          columnSizingStart,
          isResizingColumn: column.id
        }));
      };
    };
  },
  createTable: (table2) => {
    table2.setColumnSizing = (updater) => table2.options.onColumnSizingChange == null ? void 0 : table2.options.onColumnSizingChange(updater);
    table2.setColumnSizingInfo = (updater) => table2.options.onColumnSizingInfoChange == null ? void 0 : table2.options.onColumnSizingInfoChange(updater);
    table2.resetColumnSizing = (defaultState) => {
      var _table$initialState$c;
      table2.setColumnSizing(defaultState ? {} : (_table$initialState$c = table2.initialState.columnSizing) != null ? _table$initialState$c : {});
    };
    table2.resetHeaderSizeInfo = (defaultState) => {
      var _table$initialState$c2;
      table2.setColumnSizingInfo(defaultState ? getDefaultColumnSizingInfoState() : (_table$initialState$c2 = table2.initialState.columnSizingInfo) != null ? _table$initialState$c2 : getDefaultColumnSizingInfoState());
    };
    table2.getTotalSize = () => {
      var _table$getHeaderGroup, _table$getHeaderGroup2;
      return (_table$getHeaderGroup = (_table$getHeaderGroup2 = table2.getHeaderGroups()[0]) == null ? void 0 : _table$getHeaderGroup2.headers.reduce((sum2, header) => {
        return sum2 + header.getSize();
      }, 0)) != null ? _table$getHeaderGroup : 0;
    };
    table2.getLeftTotalSize = () => {
      var _table$getLeftHeaderG, _table$getLeftHeaderG2;
      return (_table$getLeftHeaderG = (_table$getLeftHeaderG2 = table2.getLeftHeaderGroups()[0]) == null ? void 0 : _table$getLeftHeaderG2.headers.reduce((sum2, header) => {
        return sum2 + header.getSize();
      }, 0)) != null ? _table$getLeftHeaderG : 0;
    };
    table2.getCenterTotalSize = () => {
      var _table$getCenterHeade, _table$getCenterHeade2;
      return (_table$getCenterHeade = (_table$getCenterHeade2 = table2.getCenterHeaderGroups()[0]) == null ? void 0 : _table$getCenterHeade2.headers.reduce((sum2, header) => {
        return sum2 + header.getSize();
      }, 0)) != null ? _table$getCenterHeade : 0;
    };
    table2.getRightTotalSize = () => {
      var _table$getRightHeader, _table$getRightHeader2;
      return (_table$getRightHeader = (_table$getRightHeader2 = table2.getRightHeaderGroups()[0]) == null ? void 0 : _table$getRightHeader2.headers.reduce((sum2, header) => {
        return sum2 + header.getSize();
      }, 0)) != null ? _table$getRightHeader : 0;
    };
  }
};
let passiveSupported = null;
function passiveEventSupported() {
  if (typeof passiveSupported === "boolean") return passiveSupported;
  let supported = false;
  try {
    const options = {
      get passive() {
        supported = true;
        return false;
      }
    };
    const noop2 = () => {
    };
    window.addEventListener("test", noop2, options);
    window.removeEventListener("test", noop2);
  } catch (err) {
    supported = false;
  }
  passiveSupported = supported;
  return passiveSupported;
}
function isTouchStartEvent(e) {
  return e.type === "touchstart";
}
const ColumnVisibility = {
  getInitialState: (state) => {
    return {
      columnVisibility: {},
      ...state
    };
  },
  getDefaultOptions: (table2) => {
    return {
      onColumnVisibilityChange: makeStateUpdater("columnVisibility", table2)
    };
  },
  createColumn: (column, table2) => {
    column.toggleVisibility = (value) => {
      if (column.getCanHide()) {
        table2.setColumnVisibility((old) => ({
          ...old,
          [column.id]: value != null ? value : !column.getIsVisible()
        }));
      }
    };
    column.getIsVisible = () => {
      var _ref, _table$getState$colum;
      const childColumns = column.columns;
      return (_ref = childColumns.length ? childColumns.some((c) => c.getIsVisible()) : (_table$getState$colum = table2.getState().columnVisibility) == null ? void 0 : _table$getState$colum[column.id]) != null ? _ref : true;
    };
    column.getCanHide = () => {
      var _column$columnDef$ena, _table$options$enable;
      return ((_column$columnDef$ena = column.columnDef.enableHiding) != null ? _column$columnDef$ena : true) && ((_table$options$enable = table2.options.enableHiding) != null ? _table$options$enable : true);
    };
    column.getToggleVisibilityHandler = () => {
      return (e) => {
        column.toggleVisibility == null || column.toggleVisibility(e.target.checked);
      };
    };
  },
  createRow: (row2, table2) => {
    row2._getAllVisibleCells = memo$1(() => [row2.getAllCells(), table2.getState().columnVisibility], (cells) => {
      return cells.filter((cell2) => cell2.column.getIsVisible());
    }, getMemoOptions(table2.options, "debugRows"));
    row2.getVisibleCells = memo$1(() => [row2.getLeftVisibleCells(), row2.getCenterVisibleCells(), row2.getRightVisibleCells()], (left, center, right) => [...left, ...center, ...right], getMemoOptions(table2.options, "debugRows"));
  },
  createTable: (table2) => {
    const makeVisibleColumnsMethod = (key, getColumns) => {
      return memo$1(() => [getColumns(), getColumns().filter((d) => d.getIsVisible()).map((d) => d.id).join("_")], (columns) => {
        return columns.filter((d) => d.getIsVisible == null ? void 0 : d.getIsVisible());
      }, getMemoOptions(table2.options, "debugColumns"));
    };
    table2.getVisibleFlatColumns = makeVisibleColumnsMethod("getVisibleFlatColumns", () => table2.getAllFlatColumns());
    table2.getVisibleLeafColumns = makeVisibleColumnsMethod("getVisibleLeafColumns", () => table2.getAllLeafColumns());
    table2.getLeftVisibleLeafColumns = makeVisibleColumnsMethod("getLeftVisibleLeafColumns", () => table2.getLeftLeafColumns());
    table2.getRightVisibleLeafColumns = makeVisibleColumnsMethod("getRightVisibleLeafColumns", () => table2.getRightLeafColumns());
    table2.getCenterVisibleLeafColumns = makeVisibleColumnsMethod("getCenterVisibleLeafColumns", () => table2.getCenterLeafColumns());
    table2.setColumnVisibility = (updater) => table2.options.onColumnVisibilityChange == null ? void 0 : table2.options.onColumnVisibilityChange(updater);
    table2.resetColumnVisibility = (defaultState) => {
      var _table$initialState$c;
      table2.setColumnVisibility(defaultState ? {} : (_table$initialState$c = table2.initialState.columnVisibility) != null ? _table$initialState$c : {});
    };
    table2.toggleAllColumnsVisible = (value) => {
      var _value;
      value = (_value = value) != null ? _value : !table2.getIsAllColumnsVisible();
      table2.setColumnVisibility(table2.getAllLeafColumns().reduce((obj, column) => ({
        ...obj,
        [column.id]: !value ? !(column.getCanHide != null && column.getCanHide()) : value
      }), {}));
    };
    table2.getIsAllColumnsVisible = () => !table2.getAllLeafColumns().some((column) => !(column.getIsVisible != null && column.getIsVisible()));
    table2.getIsSomeColumnsVisible = () => table2.getAllLeafColumns().some((column) => column.getIsVisible == null ? void 0 : column.getIsVisible());
    table2.getToggleAllColumnsVisibilityHandler = () => {
      return (e) => {
        var _target;
        table2.toggleAllColumnsVisible((_target = e.target) == null ? void 0 : _target.checked);
      };
    };
  }
};
function _getVisibleLeafColumns(table2, position) {
  return !position ? table2.getVisibleLeafColumns() : position === "center" ? table2.getCenterVisibleLeafColumns() : position === "left" ? table2.getLeftVisibleLeafColumns() : table2.getRightVisibleLeafColumns();
}
const GlobalFaceting = {
  createTable: (table2) => {
    table2._getGlobalFacetedRowModel = table2.options.getFacetedRowModel && table2.options.getFacetedRowModel(table2, "__global__");
    table2.getGlobalFacetedRowModel = () => {
      if (table2.options.manualFiltering || !table2._getGlobalFacetedRowModel) {
        return table2.getPreFilteredRowModel();
      }
      return table2._getGlobalFacetedRowModel();
    };
    table2._getGlobalFacetedUniqueValues = table2.options.getFacetedUniqueValues && table2.options.getFacetedUniqueValues(table2, "__global__");
    table2.getGlobalFacetedUniqueValues = () => {
      if (!table2._getGlobalFacetedUniqueValues) {
        return /* @__PURE__ */ new Map();
      }
      return table2._getGlobalFacetedUniqueValues();
    };
    table2._getGlobalFacetedMinMaxValues = table2.options.getFacetedMinMaxValues && table2.options.getFacetedMinMaxValues(table2, "__global__");
    table2.getGlobalFacetedMinMaxValues = () => {
      if (!table2._getGlobalFacetedMinMaxValues) {
        return;
      }
      return table2._getGlobalFacetedMinMaxValues();
    };
  }
};
const GlobalFiltering = {
  getInitialState: (state) => {
    return {
      globalFilter: void 0,
      ...state
    };
  },
  getDefaultOptions: (table2) => {
    return {
      onGlobalFilterChange: makeStateUpdater("globalFilter", table2),
      globalFilterFn: "auto",
      getColumnCanGlobalFilter: (column) => {
        var _table$getCoreRowMode;
        const value = (_table$getCoreRowMode = table2.getCoreRowModel().flatRows[0]) == null || (_table$getCoreRowMode = _table$getCoreRowMode._getAllCellsByColumnId()[column.id]) == null ? void 0 : _table$getCoreRowMode.getValue();
        return typeof value === "string" || typeof value === "number";
      }
    };
  },
  createColumn: (column, table2) => {
    column.getCanGlobalFilter = () => {
      var _column$columnDef$ena, _table$options$enable, _table$options$enable2, _table$options$getCol;
      return ((_column$columnDef$ena = column.columnDef.enableGlobalFilter) != null ? _column$columnDef$ena : true) && ((_table$options$enable = table2.options.enableGlobalFilter) != null ? _table$options$enable : true) && ((_table$options$enable2 = table2.options.enableFilters) != null ? _table$options$enable2 : true) && ((_table$options$getCol = table2.options.getColumnCanGlobalFilter == null ? void 0 : table2.options.getColumnCanGlobalFilter(column)) != null ? _table$options$getCol : true) && !!column.accessorFn;
    };
  },
  createTable: (table2) => {
    table2.getGlobalAutoFilterFn = () => {
      return filterFns.includesString;
    };
    table2.getGlobalFilterFn = () => {
      var _table$options$filter, _table$options$filter2;
      const {
        globalFilterFn
      } = table2.options;
      return isFunction(globalFilterFn) ? globalFilterFn : globalFilterFn === "auto" ? table2.getGlobalAutoFilterFn() : (_table$options$filter = (_table$options$filter2 = table2.options.filterFns) == null ? void 0 : _table$options$filter2[globalFilterFn]) != null ? _table$options$filter : filterFns[globalFilterFn];
    };
    table2.setGlobalFilter = (updater) => {
      table2.options.onGlobalFilterChange == null || table2.options.onGlobalFilterChange(updater);
    };
    table2.resetGlobalFilter = (defaultState) => {
      table2.setGlobalFilter(defaultState ? void 0 : table2.initialState.globalFilter);
    };
  }
};
const RowExpanding = {
  getInitialState: (state) => {
    return {
      expanded: {},
      ...state
    };
  },
  getDefaultOptions: (table2) => {
    return {
      onExpandedChange: makeStateUpdater("expanded", table2),
      paginateExpandedRows: true
    };
  },
  createTable: (table2) => {
    let registered = false;
    let queued = false;
    table2._autoResetExpanded = () => {
      var _ref, _table$options$autoRe;
      if (!registered) {
        table2._queue(() => {
          registered = true;
        });
        return;
      }
      if ((_ref = (_table$options$autoRe = table2.options.autoResetAll) != null ? _table$options$autoRe : table2.options.autoResetExpanded) != null ? _ref : !table2.options.manualExpanding) {
        if (queued) return;
        queued = true;
        table2._queue(() => {
          table2.resetExpanded();
          queued = false;
        });
      }
    };
    table2.setExpanded = (updater) => table2.options.onExpandedChange == null ? void 0 : table2.options.onExpandedChange(updater);
    table2.toggleAllRowsExpanded = (expanded) => {
      if (expanded != null ? expanded : !table2.getIsAllRowsExpanded()) {
        table2.setExpanded(true);
      } else {
        table2.setExpanded({});
      }
    };
    table2.resetExpanded = (defaultState) => {
      var _table$initialState$e, _table$initialState;
      table2.setExpanded(defaultState ? {} : (_table$initialState$e = (_table$initialState = table2.initialState) == null ? void 0 : _table$initialState.expanded) != null ? _table$initialState$e : {});
    };
    table2.getCanSomeRowsExpand = () => {
      return table2.getPrePaginationRowModel().flatRows.some((row2) => row2.getCanExpand());
    };
    table2.getToggleAllRowsExpandedHandler = () => {
      return (e) => {
        e.persist == null || e.persist();
        table2.toggleAllRowsExpanded();
      };
    };
    table2.getIsSomeRowsExpanded = () => {
      const expanded = table2.getState().expanded;
      return expanded === true || Object.values(expanded).some(Boolean);
    };
    table2.getIsAllRowsExpanded = () => {
      const expanded = table2.getState().expanded;
      if (typeof expanded === "boolean") {
        return expanded === true;
      }
      if (!Object.keys(expanded).length) {
        return false;
      }
      if (table2.getRowModel().flatRows.some((row2) => !row2.getIsExpanded())) {
        return false;
      }
      return true;
    };
    table2.getExpandedDepth = () => {
      let maxDepth = 0;
      const rowIds = table2.getState().expanded === true ? Object.keys(table2.getRowModel().rowsById) : Object.keys(table2.getState().expanded);
      rowIds.forEach((id) => {
        const splitId = id.split(".");
        maxDepth = Math.max(maxDepth, splitId.length);
      });
      return maxDepth;
    };
    table2.getPreExpandedRowModel = () => table2.getSortedRowModel();
    table2.getExpandedRowModel = () => {
      if (!table2._getExpandedRowModel && table2.options.getExpandedRowModel) {
        table2._getExpandedRowModel = table2.options.getExpandedRowModel(table2);
      }
      if (table2.options.manualExpanding || !table2._getExpandedRowModel) {
        return table2.getPreExpandedRowModel();
      }
      return table2._getExpandedRowModel();
    };
  },
  createRow: (row2, table2) => {
    row2.toggleExpanded = (expanded) => {
      table2.setExpanded((old) => {
        var _expanded;
        const exists = old === true ? true : !!(old != null && old[row2.id]);
        let oldExpanded = {};
        if (old === true) {
          Object.keys(table2.getRowModel().rowsById).forEach((rowId) => {
            oldExpanded[rowId] = true;
          });
        } else {
          oldExpanded = old;
        }
        expanded = (_expanded = expanded) != null ? _expanded : !exists;
        if (!exists && expanded) {
          return {
            ...oldExpanded,
            [row2.id]: true
          };
        }
        if (exists && !expanded) {
          const {
            [row2.id]: _,
            ...rest
          } = oldExpanded;
          return rest;
        }
        return old;
      });
    };
    row2.getIsExpanded = () => {
      var _table$options$getIsR;
      const expanded = table2.getState().expanded;
      return !!((_table$options$getIsR = table2.options.getIsRowExpanded == null ? void 0 : table2.options.getIsRowExpanded(row2)) != null ? _table$options$getIsR : expanded === true || (expanded == null ? void 0 : expanded[row2.id]));
    };
    row2.getCanExpand = () => {
      var _table$options$getRow, _table$options$enable, _row$subRows;
      return (_table$options$getRow = table2.options.getRowCanExpand == null ? void 0 : table2.options.getRowCanExpand(row2)) != null ? _table$options$getRow : ((_table$options$enable = table2.options.enableExpanding) != null ? _table$options$enable : true) && !!((_row$subRows = row2.subRows) != null && _row$subRows.length);
    };
    row2.getIsAllParentsExpanded = () => {
      let isFullyExpanded = true;
      let currentRow = row2;
      while (isFullyExpanded && currentRow.parentId) {
        currentRow = table2.getRow(currentRow.parentId, true);
        isFullyExpanded = currentRow.getIsExpanded();
      }
      return isFullyExpanded;
    };
    row2.getToggleExpandedHandler = () => {
      const canExpand = row2.getCanExpand();
      return () => {
        if (!canExpand) return;
        row2.toggleExpanded();
      };
    };
  }
};
const defaultPageIndex = 0;
const defaultPageSize = 10;
const getDefaultPaginationState = () => ({
  pageIndex: defaultPageIndex,
  pageSize: defaultPageSize
});
const RowPagination = {
  getInitialState: (state) => {
    return {
      ...state,
      pagination: {
        ...getDefaultPaginationState(),
        ...state == null ? void 0 : state.pagination
      }
    };
  },
  getDefaultOptions: (table2) => {
    return {
      onPaginationChange: makeStateUpdater("pagination", table2)
    };
  },
  createTable: (table2) => {
    let registered = false;
    let queued = false;
    table2._autoResetPageIndex = () => {
      var _ref, _table$options$autoRe;
      if (!registered) {
        table2._queue(() => {
          registered = true;
        });
        return;
      }
      if ((_ref = (_table$options$autoRe = table2.options.autoResetAll) != null ? _table$options$autoRe : table2.options.autoResetPageIndex) != null ? _ref : !table2.options.manualPagination) {
        if (queued) return;
        queued = true;
        table2._queue(() => {
          table2.resetPageIndex();
          queued = false;
        });
      }
    };
    table2.setPagination = (updater) => {
      const safeUpdater = (old) => {
        let newState = functionalUpdate(updater, old);
        return newState;
      };
      return table2.options.onPaginationChange == null ? void 0 : table2.options.onPaginationChange(safeUpdater);
    };
    table2.resetPagination = (defaultState) => {
      var _table$initialState$p;
      table2.setPagination(defaultState ? getDefaultPaginationState() : (_table$initialState$p = table2.initialState.pagination) != null ? _table$initialState$p : getDefaultPaginationState());
    };
    table2.setPageIndex = (updater) => {
      table2.setPagination((old) => {
        let pageIndex = functionalUpdate(updater, old.pageIndex);
        const maxPageIndex = typeof table2.options.pageCount === "undefined" || table2.options.pageCount === -1 ? Number.MAX_SAFE_INTEGER : table2.options.pageCount - 1;
        pageIndex = Math.max(0, Math.min(pageIndex, maxPageIndex));
        return {
          ...old,
          pageIndex
        };
      });
    };
    table2.resetPageIndex = (defaultState) => {
      var _table$initialState$p2, _table$initialState;
      table2.setPageIndex(defaultState ? defaultPageIndex : (_table$initialState$p2 = (_table$initialState = table2.initialState) == null || (_table$initialState = _table$initialState.pagination) == null ? void 0 : _table$initialState.pageIndex) != null ? _table$initialState$p2 : defaultPageIndex);
    };
    table2.resetPageSize = (defaultState) => {
      var _table$initialState$p3, _table$initialState2;
      table2.setPageSize(defaultState ? defaultPageSize : (_table$initialState$p3 = (_table$initialState2 = table2.initialState) == null || (_table$initialState2 = _table$initialState2.pagination) == null ? void 0 : _table$initialState2.pageSize) != null ? _table$initialState$p3 : defaultPageSize);
    };
    table2.setPageSize = (updater) => {
      table2.setPagination((old) => {
        const pageSize = Math.max(1, functionalUpdate(updater, old.pageSize));
        const topRowIndex = old.pageSize * old.pageIndex;
        const pageIndex = Math.floor(topRowIndex / pageSize);
        return {
          ...old,
          pageIndex,
          pageSize
        };
      });
    };
    table2.setPageCount = (updater) => table2.setPagination((old) => {
      var _table$options$pageCo;
      let newPageCount = functionalUpdate(updater, (_table$options$pageCo = table2.options.pageCount) != null ? _table$options$pageCo : -1);
      if (typeof newPageCount === "number") {
        newPageCount = Math.max(-1, newPageCount);
      }
      return {
        ...old,
        pageCount: newPageCount
      };
    });
    table2.getPageOptions = memo$1(() => [table2.getPageCount()], (pageCount) => {
      let pageOptions = [];
      if (pageCount && pageCount > 0) {
        pageOptions = [...new Array(pageCount)].fill(null).map((_, i) => i);
      }
      return pageOptions;
    }, getMemoOptions(table2.options, "debugTable"));
    table2.getCanPreviousPage = () => table2.getState().pagination.pageIndex > 0;
    table2.getCanNextPage = () => {
      const {
        pageIndex
      } = table2.getState().pagination;
      const pageCount = table2.getPageCount();
      if (pageCount === -1) {
        return true;
      }
      if (pageCount === 0) {
        return false;
      }
      return pageIndex < pageCount - 1;
    };
    table2.previousPage = () => {
      return table2.setPageIndex((old) => old - 1);
    };
    table2.nextPage = () => {
      return table2.setPageIndex((old) => {
        return old + 1;
      });
    };
    table2.firstPage = () => {
      return table2.setPageIndex(0);
    };
    table2.lastPage = () => {
      return table2.setPageIndex(table2.getPageCount() - 1);
    };
    table2.getPrePaginationRowModel = () => table2.getExpandedRowModel();
    table2.getPaginationRowModel = () => {
      if (!table2._getPaginationRowModel && table2.options.getPaginationRowModel) {
        table2._getPaginationRowModel = table2.options.getPaginationRowModel(table2);
      }
      if (table2.options.manualPagination || !table2._getPaginationRowModel) {
        return table2.getPrePaginationRowModel();
      }
      return table2._getPaginationRowModel();
    };
    table2.getPageCount = () => {
      var _table$options$pageCo2;
      return (_table$options$pageCo2 = table2.options.pageCount) != null ? _table$options$pageCo2 : Math.ceil(table2.getRowCount() / table2.getState().pagination.pageSize);
    };
    table2.getRowCount = () => {
      var _table$options$rowCou;
      return (_table$options$rowCou = table2.options.rowCount) != null ? _table$options$rowCou : table2.getPrePaginationRowModel().rows.length;
    };
  }
};
const getDefaultRowPinningState = () => ({
  top: [],
  bottom: []
});
const RowPinning = {
  getInitialState: (state) => {
    return {
      rowPinning: getDefaultRowPinningState(),
      ...state
    };
  },
  getDefaultOptions: (table2) => {
    return {
      onRowPinningChange: makeStateUpdater("rowPinning", table2)
    };
  },
  createRow: (row2, table2) => {
    row2.pin = (position, includeLeafRows, includeParentRows) => {
      const leafRowIds = includeLeafRows ? row2.getLeafRows().map((_ref) => {
        let {
          id
        } = _ref;
        return id;
      }) : [];
      const parentRowIds = includeParentRows ? row2.getParentRows().map((_ref2) => {
        let {
          id
        } = _ref2;
        return id;
      }) : [];
      const rowIds = /* @__PURE__ */ new Set([...parentRowIds, row2.id, ...leafRowIds]);
      table2.setRowPinning((old) => {
        var _old$top3, _old$bottom3;
        if (position === "bottom") {
          var _old$top, _old$bottom;
          return {
            top: ((_old$top = old == null ? void 0 : old.top) != null ? _old$top : []).filter((d) => !(rowIds != null && rowIds.has(d))),
            bottom: [...((_old$bottom = old == null ? void 0 : old.bottom) != null ? _old$bottom : []).filter((d) => !(rowIds != null && rowIds.has(d))), ...Array.from(rowIds)]
          };
        }
        if (position === "top") {
          var _old$top2, _old$bottom2;
          return {
            top: [...((_old$top2 = old == null ? void 0 : old.top) != null ? _old$top2 : []).filter((d) => !(rowIds != null && rowIds.has(d))), ...Array.from(rowIds)],
            bottom: ((_old$bottom2 = old == null ? void 0 : old.bottom) != null ? _old$bottom2 : []).filter((d) => !(rowIds != null && rowIds.has(d)))
          };
        }
        return {
          top: ((_old$top3 = old == null ? void 0 : old.top) != null ? _old$top3 : []).filter((d) => !(rowIds != null && rowIds.has(d))),
          bottom: ((_old$bottom3 = old == null ? void 0 : old.bottom) != null ? _old$bottom3 : []).filter((d) => !(rowIds != null && rowIds.has(d)))
        };
      });
    };
    row2.getCanPin = () => {
      var _ref3;
      const {
        enableRowPinning,
        enablePinning
      } = table2.options;
      if (typeof enableRowPinning === "function") {
        return enableRowPinning(row2);
      }
      return (_ref3 = enableRowPinning != null ? enableRowPinning : enablePinning) != null ? _ref3 : true;
    };
    row2.getIsPinned = () => {
      const rowIds = [row2.id];
      const {
        top,
        bottom
      } = table2.getState().rowPinning;
      const isTop = rowIds.some((d) => top == null ? void 0 : top.includes(d));
      const isBottom = rowIds.some((d) => bottom == null ? void 0 : bottom.includes(d));
      return isTop ? "top" : isBottom ? "bottom" : false;
    };
    row2.getPinnedIndex = () => {
      var _ref4, _visiblePinnedRowIds$;
      const position = row2.getIsPinned();
      if (!position) return -1;
      const visiblePinnedRowIds = (_ref4 = position === "top" ? table2.getTopRows() : table2.getBottomRows()) == null ? void 0 : _ref4.map((_ref5) => {
        let {
          id
        } = _ref5;
        return id;
      });
      return (_visiblePinnedRowIds$ = visiblePinnedRowIds == null ? void 0 : visiblePinnedRowIds.indexOf(row2.id)) != null ? _visiblePinnedRowIds$ : -1;
    };
  },
  createTable: (table2) => {
    table2.setRowPinning = (updater) => table2.options.onRowPinningChange == null ? void 0 : table2.options.onRowPinningChange(updater);
    table2.resetRowPinning = (defaultState) => {
      var _table$initialState$r, _table$initialState;
      return table2.setRowPinning(defaultState ? getDefaultRowPinningState() : (_table$initialState$r = (_table$initialState = table2.initialState) == null ? void 0 : _table$initialState.rowPinning) != null ? _table$initialState$r : getDefaultRowPinningState());
    };
    table2.getIsSomeRowsPinned = (position) => {
      var _pinningState$positio;
      const pinningState = table2.getState().rowPinning;
      if (!position) {
        var _pinningState$top, _pinningState$bottom;
        return Boolean(((_pinningState$top = pinningState.top) == null ? void 0 : _pinningState$top.length) || ((_pinningState$bottom = pinningState.bottom) == null ? void 0 : _pinningState$bottom.length));
      }
      return Boolean((_pinningState$positio = pinningState[position]) == null ? void 0 : _pinningState$positio.length);
    };
    table2._getPinnedRows = (visibleRows, pinnedRowIds, position) => {
      var _table$options$keepPi;
      const rows = ((_table$options$keepPi = table2.options.keepPinnedRows) != null ? _table$options$keepPi : true) ? (
        //get all rows that are pinned even if they would not be otherwise visible
        //account for expanded parent rows, but not pagination or filtering
        (pinnedRowIds != null ? pinnedRowIds : []).map((rowId) => {
          const row2 = table2.getRow(rowId, true);
          return row2.getIsAllParentsExpanded() ? row2 : null;
        })
      ) : (
        //else get only visible rows that are pinned
        (pinnedRowIds != null ? pinnedRowIds : []).map((rowId) => visibleRows.find((row2) => row2.id === rowId))
      );
      return rows.filter(Boolean).map((d) => ({
        ...d,
        position
      }));
    };
    table2.getTopRows = memo$1(() => [table2.getRowModel().rows, table2.getState().rowPinning.top], (allRows, topPinnedRowIds) => table2._getPinnedRows(allRows, topPinnedRowIds, "top"), getMemoOptions(table2.options, "debugRows"));
    table2.getBottomRows = memo$1(() => [table2.getRowModel().rows, table2.getState().rowPinning.bottom], (allRows, bottomPinnedRowIds) => table2._getPinnedRows(allRows, bottomPinnedRowIds, "bottom"), getMemoOptions(table2.options, "debugRows"));
    table2.getCenterRows = memo$1(() => [table2.getRowModel().rows, table2.getState().rowPinning.top, table2.getState().rowPinning.bottom], (allRows, top, bottom) => {
      const topAndBottom = /* @__PURE__ */ new Set([...top != null ? top : [], ...bottom != null ? bottom : []]);
      return allRows.filter((d) => !topAndBottom.has(d.id));
    }, getMemoOptions(table2.options, "debugRows"));
  }
};
const RowSelection = {
  getInitialState: (state) => {
    return {
      rowSelection: {},
      ...state
    };
  },
  getDefaultOptions: (table2) => {
    return {
      onRowSelectionChange: makeStateUpdater("rowSelection", table2),
      enableRowSelection: true,
      enableMultiRowSelection: true,
      enableSubRowSelection: true
      // enableGroupingRowSelection: false,
      // isAdditiveSelectEvent: (e: unknown) => !!e.metaKey,
      // isInclusiveSelectEvent: (e: unknown) => !!e.shiftKey,
    };
  },
  createTable: (table2) => {
    table2.setRowSelection = (updater) => table2.options.onRowSelectionChange == null ? void 0 : table2.options.onRowSelectionChange(updater);
    table2.resetRowSelection = (defaultState) => {
      var _table$initialState$r;
      return table2.setRowSelection(defaultState ? {} : (_table$initialState$r = table2.initialState.rowSelection) != null ? _table$initialState$r : {});
    };
    table2.toggleAllRowsSelected = (value) => {
      table2.setRowSelection((old) => {
        value = typeof value !== "undefined" ? value : !table2.getIsAllRowsSelected();
        const rowSelection = {
          ...old
        };
        const preGroupedFlatRows = table2.getPreGroupedRowModel().flatRows;
        if (value) {
          preGroupedFlatRows.forEach((row2) => {
            if (!row2.getCanSelect()) {
              return;
            }
            rowSelection[row2.id] = true;
          });
        } else {
          preGroupedFlatRows.forEach((row2) => {
            delete rowSelection[row2.id];
          });
        }
        return rowSelection;
      });
    };
    table2.toggleAllPageRowsSelected = (value) => table2.setRowSelection((old) => {
      const resolvedValue = typeof value !== "undefined" ? value : !table2.getIsAllPageRowsSelected();
      const rowSelection = {
        ...old
      };
      table2.getRowModel().rows.forEach((row2) => {
        mutateRowIsSelected(rowSelection, row2.id, resolvedValue, true, table2);
      });
      return rowSelection;
    });
    table2.getPreSelectedRowModel = () => table2.getCoreRowModel();
    table2.getSelectedRowModel = memo$1(() => [table2.getState().rowSelection, table2.getCoreRowModel()], (rowSelection, rowModel) => {
      if (!Object.keys(rowSelection).length) {
        return {
          rows: [],
          flatRows: [],
          rowsById: {}
        };
      }
      return selectRowsFn(table2, rowModel);
    }, getMemoOptions(table2.options, "debugTable"));
    table2.getFilteredSelectedRowModel = memo$1(() => [table2.getState().rowSelection, table2.getFilteredRowModel()], (rowSelection, rowModel) => {
      if (!Object.keys(rowSelection).length) {
        return {
          rows: [],
          flatRows: [],
          rowsById: {}
        };
      }
      return selectRowsFn(table2, rowModel);
    }, getMemoOptions(table2.options, "debugTable"));
    table2.getGroupedSelectedRowModel = memo$1(() => [table2.getState().rowSelection, table2.getSortedRowModel()], (rowSelection, rowModel) => {
      if (!Object.keys(rowSelection).length) {
        return {
          rows: [],
          flatRows: [],
          rowsById: {}
        };
      }
      return selectRowsFn(table2, rowModel);
    }, getMemoOptions(table2.options, "debugTable"));
    table2.getIsAllRowsSelected = () => {
      const preGroupedFlatRows = table2.getFilteredRowModel().flatRows;
      const {
        rowSelection
      } = table2.getState();
      let isAllRowsSelected = Boolean(preGroupedFlatRows.length && Object.keys(rowSelection).length);
      if (isAllRowsSelected) {
        if (preGroupedFlatRows.some((row2) => row2.getCanSelect() && !rowSelection[row2.id])) {
          isAllRowsSelected = false;
        }
      }
      return isAllRowsSelected;
    };
    table2.getIsAllPageRowsSelected = () => {
      const paginationFlatRows = table2.getPaginationRowModel().flatRows.filter((row2) => row2.getCanSelect());
      const {
        rowSelection
      } = table2.getState();
      let isAllPageRowsSelected = !!paginationFlatRows.length;
      if (isAllPageRowsSelected && paginationFlatRows.some((row2) => !rowSelection[row2.id])) {
        isAllPageRowsSelected = false;
      }
      return isAllPageRowsSelected;
    };
    table2.getIsSomeRowsSelected = () => {
      var _table$getState$rowSe;
      const totalSelected = Object.keys((_table$getState$rowSe = table2.getState().rowSelection) != null ? _table$getState$rowSe : {}).length;
      return totalSelected > 0 && totalSelected < table2.getFilteredRowModel().flatRows.length;
    };
    table2.getIsSomePageRowsSelected = () => {
      const paginationFlatRows = table2.getPaginationRowModel().flatRows;
      return table2.getIsAllPageRowsSelected() ? false : paginationFlatRows.filter((row2) => row2.getCanSelect()).some((d) => d.getIsSelected() || d.getIsSomeSelected());
    };
    table2.getToggleAllRowsSelectedHandler = () => {
      return (e) => {
        table2.toggleAllRowsSelected(e.target.checked);
      };
    };
    table2.getToggleAllPageRowsSelectedHandler = () => {
      return (e) => {
        table2.toggleAllPageRowsSelected(e.target.checked);
      };
    };
  },
  createRow: (row2, table2) => {
    row2.toggleSelected = (value, opts) => {
      const isSelected = row2.getIsSelected();
      table2.setRowSelection((old) => {
        var _opts$selectChildren;
        value = typeof value !== "undefined" ? value : !isSelected;
        if (row2.getCanSelect() && isSelected === value) {
          return old;
        }
        const selectedRowIds = {
          ...old
        };
        mutateRowIsSelected(selectedRowIds, row2.id, value, (_opts$selectChildren = opts == null ? void 0 : opts.selectChildren) != null ? _opts$selectChildren : true, table2);
        return selectedRowIds;
      });
    };
    row2.getIsSelected = () => {
      const {
        rowSelection
      } = table2.getState();
      return isRowSelected(row2, rowSelection);
    };
    row2.getIsSomeSelected = () => {
      const {
        rowSelection
      } = table2.getState();
      return isSubRowSelected(row2, rowSelection) === "some";
    };
    row2.getIsAllSubRowsSelected = () => {
      const {
        rowSelection
      } = table2.getState();
      return isSubRowSelected(row2, rowSelection) === "all";
    };
    row2.getCanSelect = () => {
      var _table$options$enable;
      if (typeof table2.options.enableRowSelection === "function") {
        return table2.options.enableRowSelection(row2);
      }
      return (_table$options$enable = table2.options.enableRowSelection) != null ? _table$options$enable : true;
    };
    row2.getCanSelectSubRows = () => {
      var _table$options$enable2;
      if (typeof table2.options.enableSubRowSelection === "function") {
        return table2.options.enableSubRowSelection(row2);
      }
      return (_table$options$enable2 = table2.options.enableSubRowSelection) != null ? _table$options$enable2 : true;
    };
    row2.getCanMultiSelect = () => {
      var _table$options$enable3;
      if (typeof table2.options.enableMultiRowSelection === "function") {
        return table2.options.enableMultiRowSelection(row2);
      }
      return (_table$options$enable3 = table2.options.enableMultiRowSelection) != null ? _table$options$enable3 : true;
    };
    row2.getToggleSelectedHandler = () => {
      const canSelect = row2.getCanSelect();
      return (e) => {
        var _target;
        if (!canSelect) return;
        row2.toggleSelected((_target = e.target) == null ? void 0 : _target.checked);
      };
    };
  }
};
const mutateRowIsSelected = (selectedRowIds, id, value, includeChildren, table2) => {
  var _row$subRows;
  const row2 = table2.getRow(id, true);
  if (value) {
    if (!row2.getCanMultiSelect()) {
      Object.keys(selectedRowIds).forEach((key) => delete selectedRowIds[key]);
    }
    if (row2.getCanSelect()) {
      selectedRowIds[id] = true;
    }
  } else {
    delete selectedRowIds[id];
  }
  if (includeChildren && (_row$subRows = row2.subRows) != null && _row$subRows.length && row2.getCanSelectSubRows()) {
    row2.subRows.forEach((row22) => mutateRowIsSelected(selectedRowIds, row22.id, value, includeChildren, table2));
  }
};
function selectRowsFn(table2, rowModel) {
  const rowSelection = table2.getState().rowSelection;
  const newSelectedFlatRows = [];
  const newSelectedRowsById = {};
  const recurseRows = function(rows, depth) {
    return rows.map((row2) => {
      var _row$subRows2;
      const isSelected = isRowSelected(row2, rowSelection);
      if (isSelected) {
        newSelectedFlatRows.push(row2);
        newSelectedRowsById[row2.id] = row2;
      }
      if ((_row$subRows2 = row2.subRows) != null && _row$subRows2.length) {
        row2 = {
          ...row2,
          subRows: recurseRows(row2.subRows)
        };
      }
      if (isSelected) {
        return row2;
      }
    }).filter(Boolean);
  };
  return {
    rows: recurseRows(rowModel.rows),
    flatRows: newSelectedFlatRows,
    rowsById: newSelectedRowsById
  };
}
function isRowSelected(row2, selection) {
  var _selection$row$id;
  return (_selection$row$id = selection[row2.id]) != null ? _selection$row$id : false;
}
function isSubRowSelected(row2, selection, table2) {
  var _row$subRows3;
  if (!((_row$subRows3 = row2.subRows) != null && _row$subRows3.length)) return false;
  let allChildrenSelected = true;
  let someSelected = false;
  row2.subRows.forEach((subRow) => {
    if (someSelected && !allChildrenSelected) {
      return;
    }
    if (subRow.getCanSelect()) {
      if (isRowSelected(subRow, selection)) {
        someSelected = true;
      } else {
        allChildrenSelected = false;
      }
    }
    if (subRow.subRows && subRow.subRows.length) {
      const subRowChildrenSelected = isSubRowSelected(subRow, selection);
      if (subRowChildrenSelected === "all") {
        someSelected = true;
      } else if (subRowChildrenSelected === "some") {
        someSelected = true;
        allChildrenSelected = false;
      } else {
        allChildrenSelected = false;
      }
    }
  });
  return allChildrenSelected ? "all" : someSelected ? "some" : false;
}
const reSplitAlphaNumeric = /([0-9]+)/gm;
const alphanumeric = (rowA, rowB, columnId) => {
  return compareAlphanumeric(toString(rowA.getValue(columnId)).toLowerCase(), toString(rowB.getValue(columnId)).toLowerCase());
};
const alphanumericCaseSensitive = (rowA, rowB, columnId) => {
  return compareAlphanumeric(toString(rowA.getValue(columnId)), toString(rowB.getValue(columnId)));
};
const text = (rowA, rowB, columnId) => {
  return compareBasic(toString(rowA.getValue(columnId)).toLowerCase(), toString(rowB.getValue(columnId)).toLowerCase());
};
const textCaseSensitive = (rowA, rowB, columnId) => {
  return compareBasic(toString(rowA.getValue(columnId)), toString(rowB.getValue(columnId)));
};
const datetime = (rowA, rowB, columnId) => {
  const a = rowA.getValue(columnId);
  const b = rowB.getValue(columnId);
  return a > b ? 1 : a < b ? -1 : 0;
};
const basic = (rowA, rowB, columnId) => {
  return compareBasic(rowA.getValue(columnId), rowB.getValue(columnId));
};
function compareBasic(a, b) {
  return a === b ? 0 : a > b ? 1 : -1;
}
function toString(a) {
  if (typeof a === "number") {
    if (isNaN(a) || a === Infinity || a === -Infinity) {
      return "";
    }
    return String(a);
  }
  if (typeof a === "string") {
    return a;
  }
  return "";
}
function compareAlphanumeric(aStr, bStr) {
  const a = aStr.split(reSplitAlphaNumeric).filter(Boolean);
  const b = bStr.split(reSplitAlphaNumeric).filter(Boolean);
  while (a.length && b.length) {
    const aa = a.shift();
    const bb = b.shift();
    const an = parseInt(aa, 10);
    const bn = parseInt(bb, 10);
    const combo = [an, bn].sort();
    if (isNaN(combo[0])) {
      if (aa > bb) {
        return 1;
      }
      if (bb > aa) {
        return -1;
      }
      continue;
    }
    if (isNaN(combo[1])) {
      return isNaN(an) ? -1 : 1;
    }
    if (an > bn) {
      return 1;
    }
    if (bn > an) {
      return -1;
    }
  }
  return a.length - b.length;
}
const sortingFns = {
  alphanumeric,
  alphanumericCaseSensitive,
  text,
  textCaseSensitive,
  datetime,
  basic
};
const RowSorting = {
  getInitialState: (state) => {
    return {
      sorting: [],
      ...state
    };
  },
  getDefaultColumnDef: () => {
    return {
      sortingFn: "auto",
      sortUndefined: 1
    };
  },
  getDefaultOptions: (table2) => {
    return {
      onSortingChange: makeStateUpdater("sorting", table2),
      isMultiSortEvent: (e) => {
        return e.shiftKey;
      }
    };
  },
  createColumn: (column, table2) => {
    column.getAutoSortingFn = () => {
      const firstRows = table2.getFilteredRowModel().flatRows.slice(10);
      let isString = false;
      for (const row2 of firstRows) {
        const value = row2 == null ? void 0 : row2.getValue(column.id);
        if (Object.prototype.toString.call(value) === "[object Date]") {
          return sortingFns.datetime;
        }
        if (typeof value === "string") {
          isString = true;
          if (value.split(reSplitAlphaNumeric).length > 1) {
            return sortingFns.alphanumeric;
          }
        }
      }
      if (isString) {
        return sortingFns.text;
      }
      return sortingFns.basic;
    };
    column.getAutoSortDir = () => {
      const firstRow = table2.getFilteredRowModel().flatRows[0];
      const value = firstRow == null ? void 0 : firstRow.getValue(column.id);
      if (typeof value === "string") {
        return "asc";
      }
      return "desc";
    };
    column.getSortingFn = () => {
      var _table$options$sortin, _table$options$sortin2;
      if (!column) {
        throw new Error();
      }
      return isFunction(column.columnDef.sortingFn) ? column.columnDef.sortingFn : column.columnDef.sortingFn === "auto" ? column.getAutoSortingFn() : (_table$options$sortin = (_table$options$sortin2 = table2.options.sortingFns) == null ? void 0 : _table$options$sortin2[column.columnDef.sortingFn]) != null ? _table$options$sortin : sortingFns[column.columnDef.sortingFn];
    };
    column.toggleSorting = (desc, multi) => {
      const nextSortingOrder = column.getNextSortingOrder();
      const hasManualValue = typeof desc !== "undefined" && desc !== null;
      table2.setSorting((old) => {
        const existingSorting = old == null ? void 0 : old.find((d) => d.id === column.id);
        const existingIndex = old == null ? void 0 : old.findIndex((d) => d.id === column.id);
        let newSorting = [];
        let sortAction;
        let nextDesc = hasManualValue ? desc : nextSortingOrder === "desc";
        if (old != null && old.length && column.getCanMultiSort() && multi) {
          if (existingSorting) {
            sortAction = "toggle";
          } else {
            sortAction = "add";
          }
        } else {
          if (old != null && old.length && existingIndex !== old.length - 1) {
            sortAction = "replace";
          } else if (existingSorting) {
            sortAction = "toggle";
          } else {
            sortAction = "replace";
          }
        }
        if (sortAction === "toggle") {
          if (!hasManualValue) {
            if (!nextSortingOrder) {
              sortAction = "remove";
            }
          }
        }
        if (sortAction === "add") {
          var _table$options$maxMul;
          newSorting = [...old, {
            id: column.id,
            desc: nextDesc
          }];
          newSorting.splice(0, newSorting.length - ((_table$options$maxMul = table2.options.maxMultiSortColCount) != null ? _table$options$maxMul : Number.MAX_SAFE_INTEGER));
        } else if (sortAction === "toggle") {
          newSorting = old.map((d) => {
            if (d.id === column.id) {
              return {
                ...d,
                desc: nextDesc
              };
            }
            return d;
          });
        } else if (sortAction === "remove") {
          newSorting = old.filter((d) => d.id !== column.id);
        } else {
          newSorting = [{
            id: column.id,
            desc: nextDesc
          }];
        }
        return newSorting;
      });
    };
    column.getFirstSortDir = () => {
      var _ref, _column$columnDef$sor;
      const sortDescFirst = (_ref = (_column$columnDef$sor = column.columnDef.sortDescFirst) != null ? _column$columnDef$sor : table2.options.sortDescFirst) != null ? _ref : column.getAutoSortDir() === "desc";
      return sortDescFirst ? "desc" : "asc";
    };
    column.getNextSortingOrder = (multi) => {
      var _table$options$enable, _table$options$enable2;
      const firstSortDirection = column.getFirstSortDir();
      const isSorted = column.getIsSorted();
      if (!isSorted) {
        return firstSortDirection;
      }
      if (isSorted !== firstSortDirection && ((_table$options$enable = table2.options.enableSortingRemoval) != null ? _table$options$enable : true) && // If enableSortRemove, enable in general
      (multi ? (_table$options$enable2 = table2.options.enableMultiRemove) != null ? _table$options$enable2 : true : true)) {
        return false;
      }
      return isSorted === "desc" ? "asc" : "desc";
    };
    column.getCanSort = () => {
      var _column$columnDef$ena, _table$options$enable3;
      return ((_column$columnDef$ena = column.columnDef.enableSorting) != null ? _column$columnDef$ena : true) && ((_table$options$enable3 = table2.options.enableSorting) != null ? _table$options$enable3 : true) && !!column.accessorFn;
    };
    column.getCanMultiSort = () => {
      var _ref2, _column$columnDef$ena2;
      return (_ref2 = (_column$columnDef$ena2 = column.columnDef.enableMultiSort) != null ? _column$columnDef$ena2 : table2.options.enableMultiSort) != null ? _ref2 : !!column.accessorFn;
    };
    column.getIsSorted = () => {
      var _table$getState$sorti;
      const columnSort = (_table$getState$sorti = table2.getState().sorting) == null ? void 0 : _table$getState$sorti.find((d) => d.id === column.id);
      return !columnSort ? false : columnSort.desc ? "desc" : "asc";
    };
    column.getSortIndex = () => {
      var _table$getState$sorti2, _table$getState$sorti3;
      return (_table$getState$sorti2 = (_table$getState$sorti3 = table2.getState().sorting) == null ? void 0 : _table$getState$sorti3.findIndex((d) => d.id === column.id)) != null ? _table$getState$sorti2 : -1;
    };
    column.clearSorting = () => {
      table2.setSorting((old) => old != null && old.length ? old.filter((d) => d.id !== column.id) : []);
    };
    column.getToggleSortingHandler = () => {
      const canSort = column.getCanSort();
      return (e) => {
        if (!canSort) return;
        e.persist == null || e.persist();
        column.toggleSorting == null || column.toggleSorting(void 0, column.getCanMultiSort() ? table2.options.isMultiSortEvent == null ? void 0 : table2.options.isMultiSortEvent(e) : false);
      };
    };
  },
  createTable: (table2) => {
    table2.setSorting = (updater) => table2.options.onSortingChange == null ? void 0 : table2.options.onSortingChange(updater);
    table2.resetSorting = (defaultState) => {
      var _table$initialState$s, _table$initialState;
      table2.setSorting(defaultState ? [] : (_table$initialState$s = (_table$initialState = table2.initialState) == null ? void 0 : _table$initialState.sorting) != null ? _table$initialState$s : []);
    };
    table2.getPreSortedRowModel = () => table2.getGroupedRowModel();
    table2.getSortedRowModel = () => {
      if (!table2._getSortedRowModel && table2.options.getSortedRowModel) {
        table2._getSortedRowModel = table2.options.getSortedRowModel(table2);
      }
      if (table2.options.manualSorting || !table2._getSortedRowModel) {
        return table2.getPreSortedRowModel();
      }
      return table2._getSortedRowModel();
    };
  }
};
const builtInFeatures = [
  Headers,
  ColumnVisibility,
  ColumnOrdering,
  ColumnPinning,
  ColumnFaceting,
  ColumnFiltering,
  GlobalFaceting,
  //depends on ColumnFaceting
  GlobalFiltering,
  //depends on ColumnFiltering
  RowSorting,
  ColumnGrouping,
  //depends on RowSorting
  RowExpanding,
  RowPagination,
  RowPinning,
  RowSelection,
  ColumnSizing
];
function createTable(options) {
  var _options$_features, _options$initialState;
  const _features = [...builtInFeatures, ...(_options$_features = options._features) != null ? _options$_features : []];
  let table2 = {
    _features
  };
  const defaultOptions = table2._features.reduce((obj, feature) => {
    return Object.assign(obj, feature.getDefaultOptions == null ? void 0 : feature.getDefaultOptions(table2));
  }, {});
  const mergeOptions = (options2) => {
    if (table2.options.mergeOptions) {
      return table2.options.mergeOptions(defaultOptions, options2);
    }
    return {
      ...defaultOptions,
      ...options2
    };
  };
  const coreInitialState = {};
  let initialState = {
    ...coreInitialState,
    ...(_options$initialState = options.initialState) != null ? _options$initialState : {}
  };
  table2._features.forEach((feature) => {
    var _feature$getInitialSt;
    initialState = (_feature$getInitialSt = feature.getInitialState == null ? void 0 : feature.getInitialState(initialState)) != null ? _feature$getInitialSt : initialState;
  });
  const queued = [];
  let queuedTimeout = false;
  const coreInstance = {
    _features,
    options: {
      ...defaultOptions,
      ...options
    },
    initialState,
    _queue: (cb) => {
      queued.push(cb);
      if (!queuedTimeout) {
        queuedTimeout = true;
        Promise.resolve().then(() => {
          while (queued.length) {
            queued.shift()();
          }
          queuedTimeout = false;
        }).catch((error) => setTimeout(() => {
          throw error;
        }));
      }
    },
    reset: () => {
      table2.setState(table2.initialState);
    },
    setOptions: (updater) => {
      const newOptions = functionalUpdate(updater, table2.options);
      table2.options = mergeOptions(newOptions);
    },
    getState: () => {
      return table2.options.state;
    },
    setState: (updater) => {
      table2.options.onStateChange == null || table2.options.onStateChange(updater);
    },
    _getRowId: (row2, index, parent) => {
      var _table$options$getRow;
      return (_table$options$getRow = table2.options.getRowId == null ? void 0 : table2.options.getRowId(row2, index, parent)) != null ? _table$options$getRow : `${parent ? [parent.id, index].join(".") : index}`;
    },
    getCoreRowModel: () => {
      if (!table2._getCoreRowModel) {
        table2._getCoreRowModel = table2.options.getCoreRowModel(table2);
      }
      return table2._getCoreRowModel();
    },
    // The final calls start at the bottom of the model,
    // expanded rows, which then work their way up
    getRowModel: () => {
      return table2.getPaginationRowModel();
    },
    //in next version, we should just pass in the row model as the optional 2nd arg
    getRow: (id, searchAll) => {
      let row2 = (searchAll ? table2.getPrePaginationRowModel() : table2.getRowModel()).rowsById[id];
      if (!row2) {
        row2 = table2.getCoreRowModel().rowsById[id];
        if (!row2) {
          throw new Error();
        }
      }
      return row2;
    },
    _getDefaultColumnDef: memo$1(() => [table2.options.defaultColumn], (defaultColumn) => {
      var _defaultColumn;
      defaultColumn = (_defaultColumn = defaultColumn) != null ? _defaultColumn : {};
      return {
        header: (props) => {
          const resolvedColumnDef = props.header.column.columnDef;
          if (resolvedColumnDef.accessorKey) {
            return resolvedColumnDef.accessorKey;
          }
          if (resolvedColumnDef.accessorFn) {
            return resolvedColumnDef.id;
          }
          return null;
        },
        // footer: props => props.header.column.id,
        cell: (props) => {
          var _props$renderValue$to, _props$renderValue;
          return (_props$renderValue$to = (_props$renderValue = props.renderValue()) == null || _props$renderValue.toString == null ? void 0 : _props$renderValue.toString()) != null ? _props$renderValue$to : null;
        },
        ...table2._features.reduce((obj, feature) => {
          return Object.assign(obj, feature.getDefaultColumnDef == null ? void 0 : feature.getDefaultColumnDef());
        }, {}),
        ...defaultColumn
      };
    }, getMemoOptions(options, "debugColumns")),
    _getColumnDefs: () => table2.options.columns,
    getAllColumns: memo$1(() => [table2._getColumnDefs()], (columnDefs) => {
      const recurseColumns = function(columnDefs2, parent, depth) {
        if (depth === void 0) {
          depth = 0;
        }
        return columnDefs2.map((columnDef) => {
          const column = createColumn(table2, columnDef, depth, parent);
          const groupingColumnDef = columnDef;
          column.columns = groupingColumnDef.columns ? recurseColumns(groupingColumnDef.columns, column, depth + 1) : [];
          return column;
        });
      };
      return recurseColumns(columnDefs);
    }, getMemoOptions(options, "debugColumns")),
    getAllFlatColumns: memo$1(() => [table2.getAllColumns()], (allColumns) => {
      return allColumns.flatMap((column) => {
        return column.getFlatColumns();
      });
    }, getMemoOptions(options, "debugColumns")),
    _getAllFlatColumnsById: memo$1(() => [table2.getAllFlatColumns()], (flatColumns) => {
      return flatColumns.reduce((acc, column) => {
        acc[column.id] = column;
        return acc;
      }, {});
    }, getMemoOptions(options, "debugColumns")),
    getAllLeafColumns: memo$1(() => [table2.getAllColumns(), table2._getOrderColumnsFn()], (allColumns, orderColumns2) => {
      let leafColumns = allColumns.flatMap((column) => column.getLeafColumns());
      return orderColumns2(leafColumns);
    }, getMemoOptions(options, "debugColumns")),
    getColumn: (columnId) => {
      const column = table2._getAllFlatColumnsById()[columnId];
      return column;
    }
  };
  Object.assign(table2, coreInstance);
  for (let index = 0; index < table2._features.length; index++) {
    const feature = table2._features[index];
    feature == null || feature.createTable == null || feature.createTable(table2);
  }
  return table2;
}
function getCoreRowModel() {
  return (table2) => memo$1(() => [table2.options.data], (data) => {
    const rowModel = {
      rows: [],
      flatRows: [],
      rowsById: {}
    };
    const accessRows = function(originalRows, depth, parentRow) {
      if (depth === void 0) {
        depth = 0;
      }
      const rows = [];
      for (let i = 0; i < originalRows.length; i++) {
        const row2 = createRow(table2, table2._getRowId(originalRows[i], i, parentRow), originalRows[i], i, depth, void 0, parentRow == null ? void 0 : parentRow.id);
        rowModel.flatRows.push(row2);
        rowModel.rowsById[row2.id] = row2;
        rows.push(row2);
        if (table2.options.getSubRows) {
          var _row$originalSubRows;
          row2.originalSubRows = table2.options.getSubRows(originalRows[i], i);
          if ((_row$originalSubRows = row2.originalSubRows) != null && _row$originalSubRows.length) {
            row2.subRows = accessRows(row2.originalSubRows, depth + 1, row2);
          }
        }
      }
      return rows;
    };
    rowModel.rows = accessRows(data);
    return rowModel;
  }, getMemoOptions(table2.options, "debugTable", "getRowModel", () => table2._autoResetPageIndex()));
}
function flexRender(Comp, props) {
  return !Comp ? null : isReactComponent(Comp) ? /* @__PURE__ */ reactExports.createElement(Comp, props) : Comp;
}
function isReactComponent(component) {
  return isClassComponent(component) || typeof component === "function" || isExoticComponent(component);
}
function isClassComponent(component) {
  return typeof component === "function" && (() => {
    const proto = Object.getPrototypeOf(component);
    return proto.prototype && proto.prototype.isReactComponent;
  })();
}
function isExoticComponent(component) {
  return typeof component === "object" && typeof component.$$typeof === "symbol" && ["react.memo", "react.forward_ref"].includes(component.$$typeof.description);
}
function useReactTable(options) {
  const resolvedOptions = {
    state: {},
    // Dummy state
    onStateChange: () => {
    },
    // noop
    renderFallbackValue: null,
    ...options
  };
  const [tableRef] = reactExports.useState(() => ({
    current: createTable(resolvedOptions)
  }));
  const [state, setState] = reactExports.useState(() => tableRef.current.initialState);
  tableRef.current.setOptions((prev) => ({
    ...prev,
    ...options,
    state: {
      ...state,
      ...options.state
    },
    // Similarly, we'll maintain both our internal state and any user-provided
    // state.
    onStateChange: (updater) => {
      setState(updater);
      options.onStateChange == null || options.onStateChange(updater);
    }
  }));
  return tableRef.current;
}
function memo(getDeps, fn, opts) {
  let deps = opts.initialDeps ?? [];
  let result;
  let isInitial = true;
  function memoizedFunction() {
    var _a, _b, _c;
    let depTime;
    if (opts.key && ((_a = opts.debug) == null ? void 0 : _a.call(opts))) depTime = Date.now();
    const newDeps = getDeps();
    const depsChanged = newDeps.length !== deps.length || newDeps.some((dep, index) => deps[index] !== dep);
    if (!depsChanged) {
      return result;
    }
    deps = newDeps;
    let resultTime;
    if (opts.key && ((_b = opts.debug) == null ? void 0 : _b.call(opts))) resultTime = Date.now();
    result = fn(...newDeps);
    if (opts.key && ((_c = opts.debug) == null ? void 0 : _c.call(opts))) {
      const depEndTime = Math.round((Date.now() - depTime) * 100) / 100;
      const resultEndTime = Math.round((Date.now() - resultTime) * 100) / 100;
      const resultFpsPercentage = resultEndTime / 16;
      const pad = (str, num) => {
        str = String(str);
        while (str.length < num) {
          str = " " + str;
        }
        return str;
      };
      console.info(
        `%c⏱ ${pad(resultEndTime, 5)} /${pad(depEndTime, 5)} ms`,
        `
            font-size: .6rem;
            font-weight: bold;
            color: hsl(${Math.max(
          0,
          Math.min(120 - 120 * resultFpsPercentage, 120)
        )}deg 100% 31%);`,
        opts == null ? void 0 : opts.key
      );
    }
    if ((opts == null ? void 0 : opts.onChange) && !(isInitial && opts.skipInitialOnChange)) {
      opts.onChange(result);
    }
    isInitial = false;
    return result;
  }
  memoizedFunction.updateDeps = (newDeps) => {
    deps = newDeps;
  };
  return memoizedFunction;
}
function notUndefined(value, msg) {
  if (value === void 0) {
    throw new Error(`Unexpected undefined${""}`);
  } else {
    return value;
  }
}
const approxEqual = (a, b) => Math.abs(a - b) < 1.01;
const debounce = (targetWindow, fn, ms) => {
  let timeoutId;
  return function(...args) {
    targetWindow.clearTimeout(timeoutId);
    timeoutId = targetWindow.setTimeout(() => fn.apply(this, args), ms);
  };
};
const getRect = (element) => {
  const { offsetWidth, offsetHeight } = element;
  return { width: offsetWidth, height: offsetHeight };
};
const defaultKeyExtractor = (index) => index;
const defaultRangeExtractor = (range) => {
  const start = Math.max(range.startIndex - range.overscan, 0);
  const end = Math.min(range.endIndex + range.overscan, range.count - 1);
  const arr = [];
  for (let i = start; i <= end; i++) {
    arr.push(i);
  }
  return arr;
};
const observeElementRect = (instance, cb) => {
  const element = instance.scrollElement;
  if (!element) {
    return;
  }
  const targetWindow = instance.targetWindow;
  if (!targetWindow) {
    return;
  }
  const handler = (rect) => {
    const { width, height } = rect;
    cb({ width: Math.round(width), height: Math.round(height) });
  };
  handler(getRect(element));
  if (!targetWindow.ResizeObserver) {
    return () => {
    };
  }
  const observer = new targetWindow.ResizeObserver((entries) => {
    const run = () => {
      const entry = entries[0];
      if (entry == null ? void 0 : entry.borderBoxSize) {
        const box = entry.borderBoxSize[0];
        if (box) {
          handler({ width: box.inlineSize, height: box.blockSize });
          return;
        }
      }
      handler(getRect(element));
    };
    instance.options.useAnimationFrameWithResizeObserver ? requestAnimationFrame(run) : run();
  });
  observer.observe(element, { box: "border-box" });
  return () => {
    observer.unobserve(element);
  };
};
const addEventListenerOptions = {
  passive: true
};
const supportsScrollend = typeof window == "undefined" ? true : "onscrollend" in window;
const observeElementOffset = (instance, cb) => {
  const element = instance.scrollElement;
  if (!element) {
    return;
  }
  const targetWindow = instance.targetWindow;
  if (!targetWindow) {
    return;
  }
  let offset = 0;
  const fallback = instance.options.useScrollendEvent && supportsScrollend ? () => void 0 : debounce(
    targetWindow,
    () => {
      cb(offset, false);
    },
    instance.options.isScrollingResetDelay
  );
  const createHandler = (isScrolling) => () => {
    const { horizontal, isRtl } = instance.options;
    offset = horizontal ? element["scrollLeft"] * (isRtl && -1 || 1) : element["scrollTop"];
    fallback();
    cb(offset, isScrolling);
  };
  const handler = createHandler(true);
  const endHandler = createHandler(false);
  element.addEventListener("scroll", handler, addEventListenerOptions);
  const registerScrollendEvent = instance.options.useScrollendEvent && supportsScrollend;
  if (registerScrollendEvent) {
    element.addEventListener("scrollend", endHandler, addEventListenerOptions);
  }
  return () => {
    element.removeEventListener("scroll", handler);
    if (registerScrollendEvent) {
      element.removeEventListener("scrollend", endHandler);
    }
  };
};
const measureElement = (element, entry, instance) => {
  if (entry == null ? void 0 : entry.borderBoxSize) {
    const box = entry.borderBoxSize[0];
    if (box) {
      const size = Math.round(
        box[instance.options.horizontal ? "inlineSize" : "blockSize"]
      );
      return size;
    }
  }
  return element[instance.options.horizontal ? "offsetWidth" : "offsetHeight"];
};
const elementScroll = (offset, {
  adjustments = 0,
  behavior
}, instance) => {
  var _a, _b;
  const toOffset = offset + adjustments;
  (_b = (_a = instance.scrollElement) == null ? void 0 : _a.scrollTo) == null ? void 0 : _b.call(_a, {
    [instance.options.horizontal ? "left" : "top"]: toOffset,
    behavior
  });
};
class Virtualizer {
  constructor(opts) {
    this.unsubs = [];
    this.scrollElement = null;
    this.targetWindow = null;
    this.isScrolling = false;
    this.currentScrollToIndex = null;
    this.measurementsCache = [];
    this.itemSizeCache = /* @__PURE__ */ new Map();
    this.laneAssignments = /* @__PURE__ */ new Map();
    this.pendingMeasuredCacheIndexes = [];
    this.prevLanes = void 0;
    this.lanesChangedFlag = false;
    this.lanesSettling = false;
    this.scrollRect = null;
    this.scrollOffset = null;
    this.scrollDirection = null;
    this.scrollAdjustments = 0;
    this.elementsCache = /* @__PURE__ */ new Map();
    this.observer = /* @__PURE__ */ (() => {
      let _ro = null;
      const get = () => {
        if (_ro) {
          return _ro;
        }
        if (!this.targetWindow || !this.targetWindow.ResizeObserver) {
          return null;
        }
        return _ro = new this.targetWindow.ResizeObserver((entries) => {
          entries.forEach((entry) => {
            const run = () => {
              this._measureElement(entry.target, entry);
            };
            this.options.useAnimationFrameWithResizeObserver ? requestAnimationFrame(run) : run();
          });
        });
      };
      return {
        disconnect: () => {
          var _a;
          (_a = get()) == null ? void 0 : _a.disconnect();
          _ro = null;
        },
        observe: (target) => {
          var _a;
          return (_a = get()) == null ? void 0 : _a.observe(target, { box: "border-box" });
        },
        unobserve: (target) => {
          var _a;
          return (_a = get()) == null ? void 0 : _a.unobserve(target);
        }
      };
    })();
    this.range = null;
    this.setOptions = (opts2) => {
      Object.entries(opts2).forEach(([key, value]) => {
        if (typeof value === "undefined") delete opts2[key];
      });
      this.options = {
        debug: false,
        initialOffset: 0,
        overscan: 1,
        paddingStart: 0,
        paddingEnd: 0,
        scrollPaddingStart: 0,
        scrollPaddingEnd: 0,
        horizontal: false,
        getItemKey: defaultKeyExtractor,
        rangeExtractor: defaultRangeExtractor,
        onChange: () => {
        },
        measureElement,
        initialRect: { width: 0, height: 0 },
        scrollMargin: 0,
        gap: 0,
        indexAttribute: "data-index",
        initialMeasurementsCache: [],
        lanes: 1,
        isScrollingResetDelay: 150,
        enabled: true,
        isRtl: false,
        useScrollendEvent: false,
        useAnimationFrameWithResizeObserver: false,
        ...opts2
      };
    };
    this.notify = (sync) => {
      var _a, _b;
      (_b = (_a = this.options).onChange) == null ? void 0 : _b.call(_a, this, sync);
    };
    this.maybeNotify = memo(
      () => {
        this.calculateRange();
        return [
          this.isScrolling,
          this.range ? this.range.startIndex : null,
          this.range ? this.range.endIndex : null
        ];
      },
      (isScrolling) => {
        this.notify(isScrolling);
      },
      {
        key: false,
        debug: () => this.options.debug,
        initialDeps: [
          this.isScrolling,
          this.range ? this.range.startIndex : null,
          this.range ? this.range.endIndex : null
        ]
      }
    );
    this.cleanup = () => {
      this.unsubs.filter(Boolean).forEach((d) => d());
      this.unsubs = [];
      this.observer.disconnect();
      this.scrollElement = null;
      this.targetWindow = null;
    };
    this._didMount = () => {
      return () => {
        this.cleanup();
      };
    };
    this._willUpdate = () => {
      var _a;
      const scrollElement = this.options.enabled ? this.options.getScrollElement() : null;
      if (this.scrollElement !== scrollElement) {
        this.cleanup();
        if (!scrollElement) {
          this.maybeNotify();
          return;
        }
        this.scrollElement = scrollElement;
        if (this.scrollElement && "ownerDocument" in this.scrollElement) {
          this.targetWindow = this.scrollElement.ownerDocument.defaultView;
        } else {
          this.targetWindow = ((_a = this.scrollElement) == null ? void 0 : _a.window) ?? null;
        }
        this.elementsCache.forEach((cached) => {
          this.observer.observe(cached);
        });
        this.unsubs.push(
          this.options.observeElementRect(this, (rect) => {
            this.scrollRect = rect;
            this.maybeNotify();
          })
        );
        this.unsubs.push(
          this.options.observeElementOffset(this, (offset, isScrolling) => {
            this.scrollAdjustments = 0;
            this.scrollDirection = isScrolling ? this.getScrollOffset() < offset ? "forward" : "backward" : null;
            this.scrollOffset = offset;
            this.isScrolling = isScrolling;
            this.maybeNotify();
          })
        );
        this._scrollToOffset(this.getScrollOffset(), {
          adjustments: void 0,
          behavior: void 0
        });
      }
    };
    this.getSize = () => {
      if (!this.options.enabled) {
        this.scrollRect = null;
        return 0;
      }
      this.scrollRect = this.scrollRect ?? this.options.initialRect;
      return this.scrollRect[this.options.horizontal ? "width" : "height"];
    };
    this.getScrollOffset = () => {
      if (!this.options.enabled) {
        this.scrollOffset = null;
        return 0;
      }
      this.scrollOffset = this.scrollOffset ?? (typeof this.options.initialOffset === "function" ? this.options.initialOffset() : this.options.initialOffset);
      return this.scrollOffset;
    };
    this.getFurthestMeasurement = (measurements, index) => {
      const furthestMeasurementsFound = /* @__PURE__ */ new Map();
      const furthestMeasurements = /* @__PURE__ */ new Map();
      for (let m = index - 1; m >= 0; m--) {
        const measurement = measurements[m];
        if (furthestMeasurementsFound.has(measurement.lane)) {
          continue;
        }
        const previousFurthestMeasurement = furthestMeasurements.get(
          measurement.lane
        );
        if (previousFurthestMeasurement == null || measurement.end > previousFurthestMeasurement.end) {
          furthestMeasurements.set(measurement.lane, measurement);
        } else if (measurement.end < previousFurthestMeasurement.end) {
          furthestMeasurementsFound.set(measurement.lane, true);
        }
        if (furthestMeasurementsFound.size === this.options.lanes) {
          break;
        }
      }
      return furthestMeasurements.size === this.options.lanes ? Array.from(furthestMeasurements.values()).sort((a, b) => {
        if (a.end === b.end) {
          return a.index - b.index;
        }
        return a.end - b.end;
      })[0] : void 0;
    };
    this.getMeasurementOptions = memo(
      () => [
        this.options.count,
        this.options.paddingStart,
        this.options.scrollMargin,
        this.options.getItemKey,
        this.options.enabled,
        this.options.lanes
      ],
      (count2, paddingStart, scrollMargin, getItemKey, enabled, lanes) => {
        const lanesChanged = this.prevLanes !== void 0 && this.prevLanes !== lanes;
        if (lanesChanged) {
          this.lanesChangedFlag = true;
        }
        this.prevLanes = lanes;
        this.pendingMeasuredCacheIndexes = [];
        return {
          count: count2,
          paddingStart,
          scrollMargin,
          getItemKey,
          enabled,
          lanes
        };
      },
      {
        key: false
      }
    );
    this.getMeasurements = memo(
      () => [this.getMeasurementOptions(), this.itemSizeCache],
      ({ count: count2, paddingStart, scrollMargin, getItemKey, enabled, lanes }, itemSizeCache) => {
        if (!enabled) {
          this.measurementsCache = [];
          this.itemSizeCache.clear();
          this.laneAssignments.clear();
          return [];
        }
        if (this.laneAssignments.size > count2) {
          for (const index of this.laneAssignments.keys()) {
            if (index >= count2) {
              this.laneAssignments.delete(index);
            }
          }
        }
        if (this.lanesChangedFlag) {
          this.lanesChangedFlag = false;
          this.lanesSettling = true;
          this.measurementsCache = [];
          this.itemSizeCache.clear();
          this.laneAssignments.clear();
          this.pendingMeasuredCacheIndexes = [];
        }
        if (this.measurementsCache.length === 0 && !this.lanesSettling) {
          this.measurementsCache = this.options.initialMeasurementsCache;
          this.measurementsCache.forEach((item) => {
            this.itemSizeCache.set(item.key, item.size);
          });
        }
        const min2 = this.lanesSettling ? 0 : this.pendingMeasuredCacheIndexes.length > 0 ? Math.min(...this.pendingMeasuredCacheIndexes) : 0;
        this.pendingMeasuredCacheIndexes = [];
        if (this.lanesSettling && this.measurementsCache.length === count2) {
          this.lanesSettling = false;
        }
        const measurements = this.measurementsCache.slice(0, min2);
        const laneLastIndex = new Array(lanes).fill(
          void 0
        );
        for (let m = 0; m < min2; m++) {
          const item = measurements[m];
          if (item) {
            laneLastIndex[item.lane] = m;
          }
        }
        for (let i = min2; i < count2; i++) {
          const key = getItemKey(i);
          const cachedLane = this.laneAssignments.get(i);
          let lane;
          let start;
          if (cachedLane !== void 0 && this.options.lanes > 1) {
            lane = cachedLane;
            const prevIndex = laneLastIndex[lane];
            const prevInLane = prevIndex !== void 0 ? measurements[prevIndex] : void 0;
            start = prevInLane ? prevInLane.end + this.options.gap : paddingStart + scrollMargin;
          } else {
            const furthestMeasurement = this.options.lanes === 1 ? measurements[i - 1] : this.getFurthestMeasurement(measurements, i);
            start = furthestMeasurement ? furthestMeasurement.end + this.options.gap : paddingStart + scrollMargin;
            lane = furthestMeasurement ? furthestMeasurement.lane : i % this.options.lanes;
            if (this.options.lanes > 1) {
              this.laneAssignments.set(i, lane);
            }
          }
          const measuredSize = itemSizeCache.get(key);
          const size = typeof measuredSize === "number" ? measuredSize : this.options.estimateSize(i);
          const end = start + size;
          measurements[i] = {
            index: i,
            start,
            size,
            end,
            key,
            lane
          };
          laneLastIndex[lane] = i;
        }
        this.measurementsCache = measurements;
        return measurements;
      },
      {
        key: false,
        debug: () => this.options.debug
      }
    );
    this.calculateRange = memo(
      () => [
        this.getMeasurements(),
        this.getSize(),
        this.getScrollOffset(),
        this.options.lanes
      ],
      (measurements, outerSize, scrollOffset, lanes) => {
        return this.range = measurements.length > 0 && outerSize > 0 ? calculateRange({
          measurements,
          outerSize,
          scrollOffset,
          lanes
        }) : null;
      },
      {
        key: false,
        debug: () => this.options.debug
      }
    );
    this.getVirtualIndexes = memo(
      () => {
        let startIndex = null;
        let endIndex = null;
        const range = this.calculateRange();
        if (range) {
          startIndex = range.startIndex;
          endIndex = range.endIndex;
        }
        this.maybeNotify.updateDeps([this.isScrolling, startIndex, endIndex]);
        return [
          this.options.rangeExtractor,
          this.options.overscan,
          this.options.count,
          startIndex,
          endIndex
        ];
      },
      (rangeExtractor, overscan, count2, startIndex, endIndex) => {
        return startIndex === null || endIndex === null ? [] : rangeExtractor({
          startIndex,
          endIndex,
          overscan,
          count: count2
        });
      },
      {
        key: false,
        debug: () => this.options.debug
      }
    );
    this.indexFromElement = (node) => {
      const attributeName = this.options.indexAttribute;
      const indexStr = node.getAttribute(attributeName);
      if (!indexStr) {
        console.warn(
          `Missing attribute name '${attributeName}={index}' on measured element.`
        );
        return -1;
      }
      return parseInt(indexStr, 10);
    };
    this._measureElement = (node, entry) => {
      const index = this.indexFromElement(node);
      const item = this.measurementsCache[index];
      if (!item) {
        return;
      }
      const key = item.key;
      const prevNode = this.elementsCache.get(key);
      if (prevNode !== node) {
        if (prevNode) {
          this.observer.unobserve(prevNode);
        }
        this.observer.observe(node);
        this.elementsCache.set(key, node);
      }
      if (node.isConnected) {
        this.resizeItem(index, this.options.measureElement(node, entry, this));
      }
    };
    this.resizeItem = (index, size) => {
      const item = this.measurementsCache[index];
      if (!item) {
        return;
      }
      const itemSize = this.itemSizeCache.get(item.key) ?? item.size;
      const delta = size - itemSize;
      if (delta !== 0) {
        if (this.shouldAdjustScrollPositionOnItemSizeChange !== void 0 ? this.shouldAdjustScrollPositionOnItemSizeChange(item, delta, this) : item.start < this.getScrollOffset() + this.scrollAdjustments) {
          this._scrollToOffset(this.getScrollOffset(), {
            adjustments: this.scrollAdjustments += delta,
            behavior: void 0
          });
        }
        this.pendingMeasuredCacheIndexes.push(item.index);
        this.itemSizeCache = new Map(this.itemSizeCache.set(item.key, size));
        this.notify(false);
      }
    };
    this.measureElement = (node) => {
      if (!node) {
        this.elementsCache.forEach((cached, key) => {
          if (!cached.isConnected) {
            this.observer.unobserve(cached);
            this.elementsCache.delete(key);
          }
        });
        return;
      }
      this._measureElement(node, void 0);
    };
    this.getVirtualItems = memo(
      () => [this.getVirtualIndexes(), this.getMeasurements()],
      (indexes, measurements) => {
        const virtualItems = [];
        for (let k = 0, len = indexes.length; k < len; k++) {
          const i = indexes[k];
          const measurement = measurements[i];
          virtualItems.push(measurement);
        }
        return virtualItems;
      },
      {
        key: false,
        debug: () => this.options.debug
      }
    );
    this.getVirtualItemForOffset = (offset) => {
      const measurements = this.getMeasurements();
      if (measurements.length === 0) {
        return void 0;
      }
      return notUndefined(
        measurements[findNearestBinarySearch(
          0,
          measurements.length - 1,
          (index) => notUndefined(measurements[index]).start,
          offset
        )]
      );
    };
    this.getMaxScrollOffset = () => {
      if (!this.scrollElement) return 0;
      if ("scrollHeight" in this.scrollElement) {
        return this.options.horizontal ? this.scrollElement.scrollWidth - this.scrollElement.clientWidth : this.scrollElement.scrollHeight - this.scrollElement.clientHeight;
      } else {
        const doc = this.scrollElement.document.documentElement;
        return this.options.horizontal ? doc.scrollWidth - this.scrollElement.innerWidth : doc.scrollHeight - this.scrollElement.innerHeight;
      }
    };
    this.getOffsetForAlignment = (toOffset, align, itemSize = 0) => {
      if (!this.scrollElement) return 0;
      const size = this.getSize();
      const scrollOffset = this.getScrollOffset();
      if (align === "auto") {
        align = toOffset >= scrollOffset + size ? "end" : "start";
      }
      if (align === "center") {
        toOffset += (itemSize - size) / 2;
      } else if (align === "end") {
        toOffset -= size;
      }
      const maxOffset = this.getMaxScrollOffset();
      return Math.max(Math.min(maxOffset, toOffset), 0);
    };
    this.getOffsetForIndex = (index, align = "auto") => {
      index = Math.max(0, Math.min(index, this.options.count - 1));
      const item = this.measurementsCache[index];
      if (!item) {
        return void 0;
      }
      const size = this.getSize();
      const scrollOffset = this.getScrollOffset();
      if (align === "auto") {
        if (item.end >= scrollOffset + size - this.options.scrollPaddingEnd) {
          align = "end";
        } else if (item.start <= scrollOffset + this.options.scrollPaddingStart) {
          align = "start";
        } else {
          return [scrollOffset, align];
        }
      }
      if (align === "end" && index === this.options.count - 1) {
        return [this.getMaxScrollOffset(), align];
      }
      const toOffset = align === "end" ? item.end + this.options.scrollPaddingEnd : item.start - this.options.scrollPaddingStart;
      return [
        this.getOffsetForAlignment(toOffset, align, item.size),
        align
      ];
    };
    this.isDynamicMode = () => this.elementsCache.size > 0;
    this.scrollToOffset = (toOffset, { align = "start", behavior } = {}) => {
      if (behavior === "smooth" && this.isDynamicMode()) {
        console.warn(
          "The `smooth` scroll behavior is not fully supported with dynamic size."
        );
      }
      this._scrollToOffset(this.getOffsetForAlignment(toOffset, align), {
        adjustments: void 0,
        behavior
      });
    };
    this.scrollToIndex = (index, { align: initialAlign = "auto", behavior } = {}) => {
      if (behavior === "smooth" && this.isDynamicMode()) {
        console.warn(
          "The `smooth` scroll behavior is not fully supported with dynamic size."
        );
      }
      index = Math.max(0, Math.min(index, this.options.count - 1));
      this.currentScrollToIndex = index;
      let attempts = 0;
      const maxAttempts = 10;
      const tryScroll = (currentAlign) => {
        if (!this.targetWindow) return;
        const offsetInfo = this.getOffsetForIndex(index, currentAlign);
        if (!offsetInfo) {
          console.warn("Failed to get offset for index:", index);
          return;
        }
        const [offset, align] = offsetInfo;
        this._scrollToOffset(offset, { adjustments: void 0, behavior });
        this.targetWindow.requestAnimationFrame(() => {
          const verify = () => {
            if (this.currentScrollToIndex !== index) return;
            const currentOffset = this.getScrollOffset();
            const afterInfo = this.getOffsetForIndex(index, align);
            if (!afterInfo) {
              console.warn("Failed to get offset for index:", index);
              return;
            }
            if (!approxEqual(afterInfo[0], currentOffset)) {
              scheduleRetry(align);
            }
          };
          if (this.isDynamicMode()) {
            this.targetWindow.requestAnimationFrame(verify);
          } else {
            verify();
          }
        });
      };
      const scheduleRetry = (align) => {
        if (!this.targetWindow) return;
        if (this.currentScrollToIndex !== index) return;
        attempts++;
        if (attempts < maxAttempts) {
          this.targetWindow.requestAnimationFrame(() => tryScroll(align));
        } else {
          console.warn(
            `Failed to scroll to index ${index} after ${maxAttempts} attempts.`
          );
        }
      };
      tryScroll(initialAlign);
    };
    this.scrollBy = (delta, { behavior } = {}) => {
      if (behavior === "smooth" && this.isDynamicMode()) {
        console.warn(
          "The `smooth` scroll behavior is not fully supported with dynamic size."
        );
      }
      this._scrollToOffset(this.getScrollOffset() + delta, {
        adjustments: void 0,
        behavior
      });
    };
    this.getTotalSize = () => {
      var _a;
      const measurements = this.getMeasurements();
      let end;
      if (measurements.length === 0) {
        end = this.options.paddingStart;
      } else if (this.options.lanes === 1) {
        end = ((_a = measurements[measurements.length - 1]) == null ? void 0 : _a.end) ?? 0;
      } else {
        const endByLane = Array(this.options.lanes).fill(null);
        let endIndex = measurements.length - 1;
        while (endIndex >= 0 && endByLane.some((val) => val === null)) {
          const item = measurements[endIndex];
          if (endByLane[item.lane] === null) {
            endByLane[item.lane] = item.end;
          }
          endIndex--;
        }
        end = Math.max(...endByLane.filter((val) => val !== null));
      }
      return Math.max(
        end - this.options.scrollMargin + this.options.paddingEnd,
        0
      );
    };
    this._scrollToOffset = (offset, {
      adjustments,
      behavior
    }) => {
      this.options.scrollToFn(offset, { behavior, adjustments }, this);
    };
    this.measure = () => {
      this.itemSizeCache = /* @__PURE__ */ new Map();
      this.laneAssignments = /* @__PURE__ */ new Map();
      this.notify(false);
    };
    this.setOptions(opts);
  }
}
const findNearestBinarySearch = (low, high, getCurrentValue, value) => {
  while (low <= high) {
    const middle = (low + high) / 2 | 0;
    const currentValue = getCurrentValue(middle);
    if (currentValue < value) {
      low = middle + 1;
    } else if (currentValue > value) {
      high = middle - 1;
    } else {
      return middle;
    }
  }
  if (low > 0) {
    return low - 1;
  } else {
    return 0;
  }
};
function calculateRange({
  measurements,
  outerSize,
  scrollOffset,
  lanes
}) {
  const lastIndex = measurements.length - 1;
  const getOffset = (index) => measurements[index].start;
  if (measurements.length <= lanes) {
    return {
      startIndex: 0,
      endIndex: lastIndex
    };
  }
  let startIndex = findNearestBinarySearch(
    0,
    lastIndex,
    getOffset,
    scrollOffset
  );
  let endIndex = startIndex;
  if (lanes === 1) {
    while (endIndex < lastIndex && measurements[endIndex].end < scrollOffset + outerSize) {
      endIndex++;
    }
  } else if (lanes > 1) {
    const endPerLane = Array(lanes).fill(0);
    while (endIndex < lastIndex && endPerLane.some((pos) => pos < scrollOffset + outerSize)) {
      const item = measurements[endIndex];
      endPerLane[item.lane] = item.end;
      endIndex++;
    }
    const startPerLane = Array(lanes).fill(scrollOffset + outerSize);
    while (startIndex >= 0 && startPerLane.some((pos) => pos >= scrollOffset)) {
      const item = measurements[startIndex];
      startPerLane[item.lane] = item.start;
      startIndex--;
    }
    startIndex = Math.max(0, startIndex - startIndex % lanes);
    endIndex = Math.min(lastIndex, endIndex + (lanes - 1 - endIndex % lanes));
  }
  return { startIndex, endIndex };
}
const useIsomorphicLayoutEffect = typeof document !== "undefined" ? reactExports.useLayoutEffect : reactExports.useEffect;
function useVirtualizerBase({
  useFlushSync = true,
  ...options
}) {
  const rerender = reactExports.useReducer(() => ({}), {})[1];
  const resolvedOptions = {
    ...options,
    onChange: (instance2, sync) => {
      var _a;
      if (useFlushSync && sync) {
        reactDomExports.flushSync(rerender);
      } else {
        rerender();
      }
      (_a = options.onChange) == null ? void 0 : _a.call(options, instance2, sync);
    }
  };
  const [instance] = reactExports.useState(
    () => new Virtualizer(resolvedOptions)
  );
  instance.setOptions(resolvedOptions);
  useIsomorphicLayoutEffect(() => {
    return instance._didMount();
  }, []);
  useIsomorphicLayoutEffect(() => {
    return instance._willUpdate();
  });
  return instance;
}
function useVirtualizer(options) {
  return useVirtualizerBase({
    observeElementRect,
    observeElementOffset,
    scrollToFn: elementScroll,
    ...options
  });
}
function getCellTitleValue(value, columnDef) {
  if (columnDef.titleValue) {
    return columnDef.titleValue(value);
  }
  if (value === void 0 || value === null) {
    return "";
  }
  if (typeof value === "object") {
    return JSON.stringify(value, null, 2);
  }
  return String(value);
}
const container = "_container_8dclc_1";
const table = "_table_8dclc_6";
const thead = "_thead_8dclc_11";
const headerRow = "_headerRow_8dclc_20";
const headerCell = "_headerCell_8dclc_26";
const headerContent = "_headerContent_8dclc_40";
const headerText = "_headerText_8dclc_53";
const sortIcon = "_sortIcon_8dclc_59";
const headerCellDragging = "_headerCellDragging_8dclc_64";
const headerCellDragOverLeft = "_headerCellDragOverLeft_8dclc_69";
const headerCellDragOverRight = "_headerCellDragOverRight_8dclc_73";
const resizer = "_resizer_8dclc_77";
const resizerActive = "_resizerActive_8dclc_103";
const tbody = "_tbody_8dclc_112";
const row = "_row_8dclc_117";
const rowSelected = "_rowSelected_8dclc_132";
const rowFocused = "_rowFocused_8dclc_136";
const cell = "_cell_8dclc_145";
const cellCenter = "_cellCenter_8dclc_159";
const headerCellCenter = "_headerCellCenter_8dclc_163";
const noMatching = "_noMatching_8dclc_167";
const styles = {
  container,
  table,
  thead,
  headerRow,
  headerCell,
  headerContent,
  headerText,
  sortIcon,
  headerCellDragging,
  headerCellDragOverLeft,
  headerCellDragOverRight,
  resizer,
  resizerActive,
  tbody,
  row,
  rowSelected,
  rowFocused,
  cell,
  cellCenter,
  headerCellCenter,
  noMatching
};
function DataGrid({
  // Data
  data,
  columns,
  getRowId,
  getRowKey,
  // State (consolidated)
  state,
  // State setter
  onStateChange,
  // Navigation
  getRowRoute,
  // Infinite scroll
  onScrollNearEnd,
  hasMore = false,
  fetchThreshold = 500,
  // Filtering
  filterSuggestions = [],
  onFilterColumnChange,
  // Column sizing
  onColumnSizingChange,
  onResetColumnSize,
  // UI
  className,
  loading = false,
  emptyMessage = "No matching items",
  noConfigMessage = "No directory configured."
}) {
  const {
    sorting,
    columnOrder,
    columnFilters,
    columnSizing,
    rowSelection,
    focusedRowId
  } = state;
  const containerRef = reactExports.useRef(null);
  const tableRef = reactExports.useRef(null);
  const navigate = useLoggingNavigate("DataGrid");
  const effectiveGetRowKey = reactExports.useCallback(
    (index, row2) => {
      if (getRowKey) {
        return getRowKey(index, row2);
      }
      if (row2) {
        return getRowId(row2);
      }
      return String(index);
    },
    [getRowKey, getRowId]
  );
  const handleColumnFilterChange = reactExports.useCallback(
    (columnId, filterType, condition) => {
      onStateChange((prev) => {
        if (condition === null) {
          const newFilters = { ...prev.columnFilters };
          delete newFilters[columnId];
          return {
            ...prev,
            columnFilters: newFilters
          };
        }
        return {
          ...prev,
          columnFilters: {
            ...prev.columnFilters,
            [columnId]: {
              columnId,
              filterType,
              condition
            }
          }
        };
      });
    },
    [onStateChange]
  );
  const handleColumnOrderChange = reactExports.useCallback(
    (updaterOrValue) => {
      onStateChange((prev) => {
        const newValue = typeof updaterOrValue === "function" ? updaterOrValue(prev.columnOrder) : updaterOrValue;
        return { ...prev, columnOrder: newValue };
      });
    },
    [onStateChange]
  );
  const handleSortingChange = reactExports.useCallback(
    (updaterOrValue) => {
      onStateChange((prev) => {
        const newValue = typeof updaterOrValue === "function" ? updaterOrValue(prev.sorting) : updaterOrValue;
        return { ...prev, sorting: newValue };
      });
    },
    [onStateChange]
  );
  const handleRowSelectionChange = reactExports.useCallback(
    (updaterOrValue) => {
      onStateChange((prev) => {
        const newValue = typeof updaterOrValue === "function" ? updaterOrValue(prev.rowSelection) : updaterOrValue;
        return { ...prev, rowSelection: newValue };
      });
    },
    [onStateChange]
  );
  const handleColumnSizingChange = reactExports.useCallback(
    (updaterOrValue) => {
      onStateChange((prev) => {
        const newValue = typeof updaterOrValue === "function" ? updaterOrValue(prev.columnSizing) : updaterOrValue;
        return { ...prev, columnSizing: newValue };
      });
      if (onColumnSizingChange) {
        const newValue = typeof updaterOrValue === "function" ? updaterOrValue(columnSizing) : updaterOrValue;
        onColumnSizingChange(newValue);
      }
    },
    [onStateChange, onColumnSizingChange, columnSizing]
  );
  const effectiveColumnOrder = reactExports.useMemo(() => {
    if (columnOrder && columnOrder.length > 0) {
      return columnOrder;
    }
    return columns.map(
      (col) => col.id ?? col.accessorKey
    );
  }, [columnOrder, columns]);
  const [draggedColumn, setDraggedColumn] = reactExports.useState(null);
  const [dragOverColumn, setDragOverColumn] = reactExports.useState(null);
  const [dropPosition, setDropPosition] = reactExports.useState(
    null
  );
  const resetDragState = reactExports.useCallback(() => {
    setDraggedColumn(null);
    setDragOverColumn(null);
    setDropPosition(null);
  }, []);
  const handleDragStart = reactExports.useCallback(
    (e, columnId) => {
      setDraggedColumn(columnId);
      e.dataTransfer.effectAllowed = "move";
    },
    []
  );
  const handleDragOver = reactExports.useCallback(
    (e, columnId) => {
      e.preventDefault();
      e.dataTransfer.dropEffect = "move";
      if (draggedColumn && draggedColumn !== columnId) {
        setDragOverColumn(columnId);
        const draggedIndex = effectiveColumnOrder.indexOf(draggedColumn);
        const targetIndex = effectiveColumnOrder.indexOf(columnId);
        setDropPosition(draggedIndex < targetIndex ? "right" : "left");
      }
    },
    [draggedColumn, effectiveColumnOrder]
  );
  const handleDragLeave = reactExports.useCallback(() => {
    setDragOverColumn(null);
    setDropPosition(null);
  }, []);
  const handleDrop = reactExports.useCallback(
    (e, targetColumnId) => {
      e.preventDefault();
      if (!draggedColumn || draggedColumn === targetColumnId) {
        resetDragState();
        return;
      }
      const draggedIndex = effectiveColumnOrder.indexOf(draggedColumn);
      const targetIndex = effectiveColumnOrder.indexOf(targetColumnId);
      if (draggedIndex === -1 || targetIndex === -1) {
        resetDragState();
        return;
      }
      const newOrder = [...effectiveColumnOrder];
      newOrder.splice(draggedIndex, 1);
      newOrder.splice(targetIndex, 0, draggedColumn);
      onStateChange((prev) => ({ ...prev, columnOrder: newOrder }));
      resetDragState();
    },
    [draggedColumn, effectiveColumnOrder, onStateChange, resetDragState]
  );
  const handleDragEnd = reactExports.useCallback(() => {
    resetDragState();
  }, [resetDragState]);
  const table2 = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
    manualSorting: true,
    columnResizeMode: "onChange",
    enableColumnResizing: true,
    enableSorting: true,
    enableMultiSort: true,
    enableSortingRemoval: true,
    maxMultiSortColCount: 3,
    enableRowSelection: true,
    getRowId,
    state: {
      columnSizing,
      columnOrder: effectiveColumnOrder,
      sorting,
      rowSelection
    },
    onColumnSizingChange: handleColumnSizingChange,
    onColumnOrderChange: handleColumnOrderChange,
    onSortingChange: handleSortingChange,
    onRowSelectionChange: handleRowSelectionChange
  });
  const { rows } = table2.getRowModel();
  const handleRowClick = reactExports.useCallback(
    (e, rowId, rowIndex) => {
      if (containerRef.current) {
        containerRef.current.focus();
      }
      onStateChange((prev) => ({ ...prev, focusedRowId: rowId }));
      const row2 = rows[rowIndex];
      if (!row2) return;
      if (e.metaKey || e.ctrlKey) {
        openRouteInNewTab(getRowRoute(row2.original));
      } else if (e.shiftKey) {
        const currentSelectedRows = Object.keys(rowSelection).filter(
          (id) => rowSelection[id]
        );
        if (currentSelectedRows.length > 0) {
          const lastSelectedId = currentSelectedRows[currentSelectedRows.length - 1];
          const lastSelectedIndex = rows.findIndex(
            (r) => r.id === lastSelectedId
          );
          if (lastSelectedIndex !== -1) {
            const start = Math.min(lastSelectedIndex, rowIndex);
            const end = Math.max(lastSelectedIndex, rowIndex);
            const newSelection = {};
            for (let i = start; i <= end; i++) {
              const r = rows[i];
              if (r) {
                newSelection[r.id] = true;
              }
            }
            onStateChange((prev) => ({
              ...prev,
              rowSelection: newSelection
            }));
          }
        } else {
          onStateChange((prev) => ({
            ...prev,
            rowSelection: { [rowId]: true }
          }));
        }
      } else {
        void navigate(getRowRoute(row2.original));
      }
    },
    [rows, rowSelection, onStateChange, navigate, getRowRoute]
  );
  const handleKeyDown = reactExports.useCallback(
    (e) => {
      if (rows.length === 0) return;
      const focusedIndex = focusedRowId ? rows.findIndex((r) => r.id === focusedRowId) : -1;
      let newFocusedIndex = focusedIndex;
      let shouldUpdateSelection = false;
      let shouldExtendSelection = false;
      switch (e.key) {
        case "ArrowDown":
          e.preventDefault();
          if (e.metaKey || e.ctrlKey) {
            newFocusedIndex = rows.length - 1;
          } else {
            newFocusedIndex = Math.min(focusedIndex + 1, rows.length - 1);
          }
          shouldUpdateSelection = !e.shiftKey;
          shouldExtendSelection = e.shiftKey;
          break;
        case "ArrowUp":
          e.preventDefault();
          if (e.metaKey || e.ctrlKey) {
            newFocusedIndex = 0;
          } else {
            newFocusedIndex = Math.max(focusedIndex - 1, 0);
          }
          shouldUpdateSelection = !e.shiftKey;
          shouldExtendSelection = e.shiftKey;
          break;
        case "Enter":
          e.preventDefault();
          if (focusedIndex !== -1) {
            const row2 = rows[focusedIndex];
            if (row2) {
              void navigate(getRowRoute(row2.original));
            }
          }
          return;
        case " ":
          e.preventDefault();
          if (focusedIndex !== -1) {
            const row2 = rows[focusedIndex];
            if (row2) {
              onStateChange((prev) => ({
                ...prev,
                rowSelection: {
                  ...prev.rowSelection,
                  [row2.id]: !prev.rowSelection[row2.id]
                }
              }));
            }
          }
          return;
        case "a":
          if (e.metaKey || e.ctrlKey) {
            e.preventDefault();
            const allSelected = {};
            rows.forEach((row2) => {
              allSelected[row2.id] = true;
            });
            onStateChange((prev) => ({
              ...prev,
              rowSelection: allSelected
            }));
          }
          return;
        case "Escape":
          e.preventDefault();
          onStateChange((prev) => ({
            ...prev,
            rowSelection: {}
          }));
          return;
        default:
          return;
      }
      if (newFocusedIndex !== focusedIndex && newFocusedIndex !== -1) {
        const newRow = rows[newFocusedIndex];
        if (!newRow) return;
        onStateChange((prev) => ({
          ...prev,
          focusedRowId: newRow.id
        }));
        if (shouldUpdateSelection) {
          onStateChange((prev) => ({
            ...prev,
            rowSelection: { [newRow.id]: true }
          }));
        } else if (shouldExtendSelection) {
          const currentSelectedRows = Object.keys(rowSelection).filter(
            (id) => rowSelection[id]
          );
          if (currentSelectedRows.length > 0) {
            const anchorId = currentSelectedRows[0];
            const anchorIndex = rows.findIndex((r) => r.id === anchorId);
            if (anchorIndex !== -1) {
              const start = Math.min(anchorIndex, newFocusedIndex);
              const end = Math.max(anchorIndex, newFocusedIndex);
              const newSelection = {};
              for (let i = start; i <= end; i++) {
                const r = rows[i];
                if (r) {
                  newSelection[r.id] = true;
                }
              }
              onStateChange((prev) => ({
                ...prev,
                rowSelection: newSelection
              }));
            }
          } else {
            onStateChange((prev) => ({
              ...prev,
              rowSelection: { [newRow.id]: true }
            }));
          }
        }
      }
    },
    [rows, focusedRowId, rowSelection, onStateChange, navigate, getRowRoute]
  );
  const rowVirtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => containerRef.current,
    estimateSize: () => 29,
    overscan: 10,
    getItemKey: (index) => effectiveGetRowKey(index, rows[index]?.original)
  });
  const virtualItems = rowVirtualizer.getVirtualItems();
  const totalSize = rowVirtualizer.getTotalSize();
  const checkScrollNearEnd = reactExports.useCallback(
    (containerRefElement) => {
      if (!containerRefElement || !hasMore || !onScrollNearEnd) return;
      const { scrollHeight, scrollTop, clientHeight } = containerRefElement;
      const distanceFromBottom = scrollHeight - scrollTop - clientHeight;
      if (distanceFromBottom < fetchThreshold) {
        onScrollNearEnd(distanceFromBottom);
      }
    },
    [onScrollNearEnd, hasMore, fetchThreshold]
  );
  reactExports.useEffect(() => {
    checkScrollNearEnd(containerRef.current);
  }, [checkScrollNearEnd]);
  reactExports.useEffect(() => {
    if (focusedRowId && containerRef.current) {
      const focusedIndex = rows.findIndex((r) => r.id === focusedRowId);
      if (focusedIndex !== -1) {
        if (focusedIndex === rows.length - 1) {
          containerRef.current.scrollTop = containerRef.current.scrollHeight;
        } else {
          rowVirtualizer.scrollToIndex(focusedIndex, {
            align: "center",
            behavior: "auto"
          });
        }
      }
    }
  }, [focusedRowId, rows, rowVirtualizer]);
  const onScroll = reactExports.useCallback(
    (e) => checkScrollNearEnd(e.currentTarget),
    [checkScrollNearEnd]
  );
  const getEmptyMessage = () => {
    if (loading) return "Loading...";
    if (!data.length && noConfigMessage) return noConfigMessage;
    return emptyMessage;
  };
  return /* @__PURE__ */ jsxRuntimeExports.jsx(
    "div",
    {
      ref: containerRef,
      className: clsx(className, styles.container),
      tabIndex: 0,
      onKeyDown: handleKeyDown,
      onScroll,
      children: /* @__PURE__ */ jsxRuntimeExports.jsxs("table", { ref: tableRef, className: styles.table, children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("thead", { className: styles.thead, children: table2.getHeaderGroups().map((headerGroup) => /* @__PURE__ */ jsxRuntimeExports.jsx("tr", { className: styles.headerRow, children: headerGroup.headers.map((header) => {
          const columnDef = header.column.columnDef;
          const columnMeta = columnDef.meta;
          const align = columnMeta?.align;
          const filterType = columnMeta?.filterType;
          return /* @__PURE__ */ jsxRuntimeExports.jsxs(
            "th",
            {
              className: clsx(
                styles.headerCell,
                draggedColumn === header.column.id && styles.headerCellDragging,
                dragOverColumn === header.column.id && dropPosition === "left" && styles.headerCellDragOverLeft,
                dragOverColumn === header.column.id && dropPosition === "right" && styles.headerCellDragOverRight
              ),
              style: { width: header.getSize() },
              onDragOver: (e) => handleDragOver(e, header.column.id),
              onDragLeave: handleDragLeave,
              onDrop: (e) => handleDrop(e, header.column.id),
              title: [header.column.id, columnDef.headerTitle].filter(Boolean).join("\n"),
              children: [
                /* @__PURE__ */ jsxRuntimeExports.jsxs(
                  "div",
                  {
                    className: clsx(
                      styles.headerContent,
                      align === "center" && styles.headerCellCenter
                    ),
                    draggable: true,
                    onDragStart: (e) => handleDragStart(e, header.column.id),
                    onDragEnd: handleDragEnd,
                    onClick: header.column.getToggleSortingHandler(),
                    style: {
                      cursor: "pointer",
                      maxWidth: `calc(${header.getSize()}px - 32px)`
                    },
                    children: [
                      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: styles.headerText, children: header.isPlaceholder ? null : flexRender(
                        header.column.columnDef.header,
                        header.getContext()
                      ) }),
                      {
                        asc: /* @__PURE__ */ jsxRuntimeExports.jsx(
                          "i",
                          {
                            className: clsx(
                              ApplicationIcons.arrows.up,
                              styles.sortIcon
                            )
                          }
                        ),
                        desc: /* @__PURE__ */ jsxRuntimeExports.jsx(
                          "i",
                          {
                            className: clsx(
                              ApplicationIcons.arrows.down,
                              styles.sortIcon
                            )
                          }
                        )
                      }[header.column.getIsSorted()] ?? null
                    ]
                  }
                ),
                columnMeta?.filterable && filterType ? /* @__PURE__ */ jsxRuntimeExports.jsx(
                  ColumnFilterControl,
                  {
                    columnId: header.column.id,
                    filterType,
                    condition: columnFilters[header.column.id]?.condition ?? null,
                    onChange: (condition) => handleColumnFilterChange(
                      header.column.id,
                      filterType,
                      condition
                    ),
                    suggestions: filterSuggestions,
                    onOpenChange: onFilterColumnChange
                  }
                ) : null,
                /* @__PURE__ */ jsxRuntimeExports.jsx(
                  "div",
                  {
                    className: clsx(
                      styles.resizer,
                      header.column.getIsResizing() && styles.resizerActive
                    ),
                    onMouseDown: header.getResizeHandler(),
                    onTouchStart: header.getResizeHandler(),
                    onDoubleClick: () => onResetColumnSize?.(header.column.id)
                  }
                )
              ]
            },
            header.id
          );
        }) }, headerGroup.id)) }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("tbody", { className: styles.tbody, style: { height: `${totalSize}px` }, children: virtualItems.length > 0 ? virtualItems.map((virtualRow) => {
          const row2 = rows[virtualRow.index];
          if (!row2) return null;
          const isSelected = row2.getIsSelected();
          const isFocused = focusedRowId === row2.id;
          const rowKey = effectiveGetRowKey(virtualRow.index, row2.original);
          return /* @__PURE__ */ jsxRuntimeExports.jsx(
            "tr",
            {
              className: clsx(
                styles.row,
                isSelected && styles.rowSelected,
                isFocused && styles.rowFocused
              ),
              style: { transform: `translateY(${virtualRow.start}px)` },
              onClick: (e) => handleRowClick(e, row2.id, virtualRow.index),
              children: row2.getVisibleCells().map((cell2) => {
                const cellColumnDef = cell2.column.columnDef;
                const cellAlign = cellColumnDef.meta?.align;
                const titleValue = getCellTitleValue(
                  cell2.getValue(),
                  cellColumnDef
                );
                return /* @__PURE__ */ jsxRuntimeExports.jsx(
                  "td",
                  {
                    className: clsx(
                      styles.cell,
                      cellAlign === "center" && styles.cellCenter
                    ),
                    style: { width: cell2.column.getSize() },
                    title: titleValue,
                    children: flexRender(
                      cell2.column.columnDef.cell,
                      cell2.getContext()
                    )
                  },
                  cell2.id
                );
              })
            },
            rowKey
          );
        }) : /* @__PURE__ */ jsxRuntimeExports.jsx("tr", { className: clsx(styles.noMatching, "text-size-smaller"), children: /* @__PURE__ */ jsxRuntimeExports.jsx("td", { children: getEmptyMessage() }) }) })
      ] })
    }
  );
}
const DEFAULT_MIN_SIZE = 40;
const DEFAULT_MAX_SIZE = 600;
const DEFAULT_SIZE = 150;
function clampSize(size, constraints) {
  return Math.max(constraints.minSize, Math.min(constraints.maxSize, size));
}
function getColumnId(column) {
  return column.id || column.accessorKey || "";
}
function getColumnConstraints(columns) {
  const constraints = /* @__PURE__ */ new Map();
  for (const column of columns) {
    const id = getColumnId(column);
    if (id) {
      constraints.set(id, {
        size: column.size ?? DEFAULT_SIZE,
        minSize: column.minSize ?? DEFAULT_MIN_SIZE,
        maxSize: column.maxSize ?? DEFAULT_MAX_SIZE
      });
    }
  }
  return constraints;
}
const defaultStrategy = {
  computeSizes({ columns }) {
    const sizing = {};
    for (const column of columns) {
      const id = getColumnId(column);
      if (id && column.size !== void 0) {
        sizing[id] = column.size;
      }
    }
    return sizing;
  }
};
function measureTextWidth(text2, font, measureContainer) {
  const span = document.createElement("span");
  span.style.cssText = `white-space: nowrap; font: ${font}; visibility: hidden; position: absolute;`;
  span.textContent = text2;
  measureContainer.appendChild(span);
  const width = span.offsetWidth;
  measureContainer.removeChild(span);
  return width;
}
function measureHeaderExtraWidth(tableElement) {
  const headerCell2 = tableElement.querySelector("th");
  if (!headerCell2) return 40;
  const headerStyle = getComputedStyle(headerCell2);
  const paddingLeft = parseFloat(headerStyle.paddingLeft) || 0;
  const paddingRight = parseFloat(headerStyle.paddingRight) || 0;
  const gap = parseFloat(headerStyle.gap) || 0;
  const filterButton = headerCell2.querySelector("button");
  const filterButtonWidth = filterButton ? filterButton.offsetWidth : 0;
  const sortIcon2 = headerCell2.querySelector("i");
  const sortIconWidth = sortIcon2 ? sortIcon2.offsetWidth + 4 : parseFloat(headerStyle.fontSize) || 12;
  return paddingLeft + paddingRight + gap * 2 + filterButtonWidth + sortIconWidth;
}
function measureCellPadding(cellElement) {
  if (!cellElement) return 16;
  const cellStyle = getComputedStyle(cellElement);
  const paddingLeft = parseFloat(cellStyle.paddingLeft) || 0;
  const paddingRight = parseFloat(cellStyle.paddingRight) || 0;
  return paddingLeft + paddingRight;
}
const fitContentStrategy = {
  computeSizes({
    tableElement,
    columns,
    data,
    constraints
  }) {
    const sizing = {};
    if (!tableElement || data.length === 0) {
      for (const column of columns) {
        const id = getColumnId(column);
        if (id) {
          sizing[id] = column.size ?? DEFAULT_SIZE;
        }
      }
      return sizing;
    }
    const measureContainer = document.createElement("div");
    measureContainer.style.cssText = "position: absolute; visibility: hidden; pointer-events: none; top: -9999px;";
    document.body.appendChild(measureContainer);
    try {
      const headerElement = tableElement.querySelector("th");
      const cellElement = tableElement.querySelector("td");
      const headerStyle = headerElement ? getComputedStyle(headerElement) : getComputedStyle(tableElement);
      const cellStyle = cellElement ? getComputedStyle(cellElement) : getComputedStyle(tableElement);
      const headerFont = headerStyle.font || "12px sans-serif";
      const cellFont = cellStyle.font || "12px sans-serif";
      const headerExtraWidth = measureHeaderExtraWidth(tableElement);
      const cellPadding = measureCellPadding(cellElement);
      const sampleSize = Math.min(50, data.length);
      for (const column of columns) {
        const id = getColumnId(column);
        const accessorKey = column.accessorKey;
        if (!id || !accessorKey) continue;
        const headerText2 = String(column.header || "");
        const headerTextWidth = measureTextWidth(
          headerText2,
          headerFont,
          measureContainer
        );
        const headerWidth = headerTextWidth + headerExtraWidth;
        const getTextValue = column.textValue ?? ((v) => v == null ? "-" : String(v));
        let maxContentWidth = 0;
        let skipContentMeasurement = false;
        for (let i = 0; i < sampleSize; i++) {
          const row2 = data[i];
          if (!row2) continue;
          const value = row2[accessorKey];
          const textContent = getTextValue(value);
          if (textContent === null) {
            skipContentMeasurement = true;
            break;
          }
          const contentWidth = measureTextWidth(
            textContent,
            cellFont,
            measureContainer
          );
          maxContentWidth = Math.max(maxContentWidth, contentWidth);
        }
        if (skipContentMeasurement) {
          maxContentWidth = 0;
        }
        const contentWidthWithPadding = maxContentWidth + cellPadding;
        const idealSize = Math.max(headerWidth, contentWidthWithPadding);
        const constraint = constraints.get(id);
        if (constraint) {
          sizing[id] = clampSize(idealSize, constraint);
        } else {
          sizing[id] = idealSize;
        }
      }
    } finally {
      document.body.removeChild(measureContainer);
    }
    return sizing;
  }
};
const sizingStrategies = {
  default: defaultStrategy,
  "fit-content": fitContentStrategy
};
function getSizingStrategy(key) {
  return sizingStrategies[key] ?? sizingStrategies.default;
}
export {
  DataGrid as D,
  getSizingStrategy as a,
  clampSize as c,
  getColumnConstraints as g
};
//# sourceMappingURL=strategies.js.map
