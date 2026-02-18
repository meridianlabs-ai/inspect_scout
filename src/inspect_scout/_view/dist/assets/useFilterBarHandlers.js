import { r as reactExports, j as jsxRuntimeExports, e as ApplicationIcons, g as clsx } from "./index.js";
import { e as formatTime, P as PopOver, T as ToolButton } from "./ToolButton.js";
import { T as ToolDropdownButton } from "./ToolDropdownButton.js";
import { A as AutocompleteInput, C as Chip } from "./Chip.js";
import { C as ConditionBuilder } from "./transcriptColumns.js";
function formatDateForInput(value) {
  if (value === null || value === void 0) {
    return "";
  }
  const date = new Date(value);
  if (isNaN(date.getTime())) {
    return "";
  }
  const dateOnly = date.toISOString().split("T")[0];
  return dateOnly ?? "";
}
function formatDateTimeForInput(value) {
  if (value === null || value === void 0) {
    return "";
  }
  const date = new Date(value);
  if (isNaN(date.getTime())) {
    return "";
  }
  const isoStr = date.toISOString();
  return isoStr.substring(0, 16);
}
function parseDateFromInput(value) {
  if (!value || value.trim() === "") {
    return void 0;
  }
  const date = new Date(value);
  if (isNaN(date.getTime())) {
    return void 0;
  }
  return date.toISOString();
}
const filterButton$1 = "_filterButton_fuk0s_1";
const filterButtonActive = "_filterButtonActive_fuk0s_12";
const styles$4 = {
  filterButton: filterButton$1,
  filterButtonActive
};
const ColumnFilterButton = reactExports.forwardRef(({ columnId: columnId2, isActive, onClick }, ref) => {
  return /* @__PURE__ */ jsxRuntimeExports.jsx(
    "button",
    {
      ref,
      type: "button",
      className: clsx(
        styles$4.filterButton,
        isActive && styles$4.filterButtonActive
      ),
      onClick,
      "aria-label": `Filter ${columnId2}`,
      children: /* @__PURE__ */ jsxRuntimeExports.jsx("i", { className: ApplicationIcons.filter })
    }
  );
});
ColumnFilterButton.displayName = "ColumnFilterButton";
const filterContent = "_filterContent_1e9kw_1";
const filterRow = "_filterRow_1e9kw_7";
const filterSelect = "_filterSelect_1e9kw_13";
const filterInput = "_filterInput_1e9kw_14";
const columnId = "_columnId_1e9kw_30";
const columnIdText = "_columnIdText_1e9kw_35";
const filterButton = "_filterButton_1e9kw_39";
const durationInputWrapper = "_durationInputWrapper_1e9kw_44";
const durationHelper = "_durationHelper_1e9kw_51";
const rangeLabel = "_rangeLabel_1e9kw_57";
const styles$3 = {
  filterContent,
  filterRow,
  filterSelect,
  filterInput,
  columnId,
  columnIdText,
  filterButton,
  durationInputWrapper,
  durationHelper,
  rangeLabel
};
const DurationInput = ({
  id,
  value,
  onChange,
  disabled,
  autoFocus
}) => {
  const parsedSeconds = reactExports.useMemo(() => {
    const num = Number(value);
    return Number.isFinite(num) && num >= 0 ? num : null;
  }, [value]);
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles$3.durationInputWrapper, children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx(
      "input",
      {
        id,
        className: styles$3.filterInput,
        type: "number",
        spellCheck: "false",
        value,
        onChange,
        placeholder: "Seconds",
        disabled,
        step: "any",
        min: "0",
        autoFocus
      }
    ),
    parsedSeconds !== null && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles$3.durationHelper, children: formatTime(parsedSeconds) })
  ] });
};
const ColumnFilterEditor = ({
  columnId: columnId2,
  filterType,
  operator,
  operatorOptions,
  rawValue,
  rawValue2 = "",
  isValueDisabled,
  isRangeOperator = false,
  onOperatorChange,
  onValueChange,
  onValue2Change,
  onCommit,
  onCancel,
  suggestions = [],
  mode = "edit",
  columns,
  onColumnChange
}) => {
  const isAddMode = mode === "add";
  const hasColumnSelected = isAddMode ? !!columnId2 : true;
  const showColumnDropdown = isAddMode && !columnId2;
  const selectedColumnLabel = columnId2 ? columns?.find((col) => col.id === columnId2)?.label ?? columnId2 : "";
  const handleColumnSelectChange = reactExports.useCallback(
    (event) => {
      onColumnChange?.(event.target.value);
    },
    [onColumnChange]
  );
  const handleOperatorChange = reactExports.useCallback(
    (event) => {
      const operator2 = event.target.value;
      onOperatorChange(operator2);
    },
    [onOperatorChange]
  );
  const handleValueChange = reactExports.useCallback(
    (event) => {
      const value = event.target.value;
      onValueChange(value);
    },
    [onValueChange]
  );
  const handleValue2Change = reactExports.useCallback(
    (event) => {
      const value = event.target.value;
      onValue2Change?.(value);
    },
    [onValue2Change]
  );
  const handleKeyDown = reactExports.useCallback(
    (event) => {
      event.stopPropagation();
      if (event.key === "Escape") {
        event.preventDefault();
        onCancel?.();
      }
      if (event.key === "Enter") {
        event.preventDefault();
        onCommit?.();
      }
    },
    [onCancel, onCommit]
  );
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles$3.filterContent, onKeyDown: handleKeyDown, children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx(
      "div",
      {
        className: clsx(
          styles$3.filterRow,
          styles$3.columnId,
          !showColumnDropdown && styles$3.columnIdText,
          "text-size-small"
        ),
        children: showColumnDropdown ? /* @__PURE__ */ jsxRuntimeExports.jsxs(
          "select",
          {
            id: "column-select",
            className: styles$3.filterSelect,
            value: columnId2,
            onChange: handleColumnSelectChange,
            autoFocus: true,
            children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "", children: "Select column..." }),
              columns?.map((col) => /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: col.id, children: col.label }, col.id))
            ]
          }
        ) : selectedColumnLabel
      }
    ),
    hasColumnSelected && /* @__PURE__ */ jsxRuntimeExports.jsxs(jsxRuntimeExports.Fragment, { children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles$3.filterRow, children: /* @__PURE__ */ jsxRuntimeExports.jsx(
        "select",
        {
          id: `${columnId2}-op`,
          className: styles$3.filterSelect,
          value: operator,
          onChange: handleOperatorChange,
          children: operatorOptions.map((option) => /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: option, children: option }, option))
        }
      ) }),
      isRangeOperator && /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: styles$3.rangeLabel, children: "Start" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles$3.filterRow, children: filterType === "boolean" ? /* @__PURE__ */ jsxRuntimeExports.jsxs(
        "select",
        {
          id: `${columnId2}-val`,
          className: styles$3.filterSelect,
          value: rawValue,
          onChange: handleValueChange,
          disabled: isValueDisabled,
          autoFocus: !isAddMode,
          children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "", children: "(not set)" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "true", children: "true" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "false", children: "false" })
          ]
        }
      ) : filterType === "string" || filterType === "unknown" ? /* @__PURE__ */ jsxRuntimeExports.jsx(
        AutocompleteInput,
        {
          id: `${columnId2}-val`,
          value: rawValue,
          onChange: onValueChange,
          onCommit,
          onCancel,
          disabled: isValueDisabled,
          placeholder: "Filter",
          suggestions,
          className: styles$3.filterInput,
          autoFocus: !isAddMode,
          allowBrowse: true
        }
      ) : filterType === "duration" ? /* @__PURE__ */ jsxRuntimeExports.jsx(
        DurationInput,
        {
          id: `${columnId2}-val`,
          value: rawValue,
          onChange: handleValueChange,
          disabled: isValueDisabled,
          autoFocus: !isAddMode
        }
      ) : /* @__PURE__ */ jsxRuntimeExports.jsx(
        "input",
        {
          id: `${columnId2}-val`,
          className: styles$3.filterInput,
          type: filterType === "number" ? "number" : filterType === "date" ? "date" : "datetime-local",
          spellCheck: "false",
          value: rawValue,
          onChange: handleValueChange,
          placeholder: "Filter",
          disabled: isValueDisabled,
          step: filterType === "number" ? "any" : void 0,
          autoFocus: !isAddMode
        }
      ) }),
      isRangeOperator && /* @__PURE__ */ jsxRuntimeExports.jsxs(jsxRuntimeExports.Fragment, { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: styles$3.rangeLabel, children: "End" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles$3.filterRow, children: filterType === "duration" ? /* @__PURE__ */ jsxRuntimeExports.jsx(
          DurationInput,
          {
            id: `${columnId2}-val2`,
            value: rawValue2,
            onChange: handleValue2Change,
            disabled: isValueDisabled
          }
        ) : /* @__PURE__ */ jsxRuntimeExports.jsx(
          "input",
          {
            id: `${columnId2}-val2`,
            className: styles$3.filterInput,
            type: filterType === "number" ? "number" : filterType === "date" ? "date" : "datetime-local",
            spellCheck: "false",
            value: rawValue2,
            onChange: handleValue2Change,
            placeholder: "Filter",
            disabled: isValueDisabled,
            step: filterType === "number" ? "any" : void 0
          }
        ) })
      ] })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles$3.filterRow, children: /* @__PURE__ */ jsxRuntimeExports.jsx(
      "button",
      {
        className: clsx(
          "btn",
          "btn-outline-primary",
          styles$3.filterButton,
          "text-size-small"
        ),
        onClick: onCommit,
        disabled: !hasColumnSelected,
        children: "Apply"
      }
    ) })
  ] });
};
const OPERATORS_BY_TYPE = {
  string: [
    "=",
    "!=",
    "LIKE",
    "NOT LIKE",
    "ILIKE",
    "NOT ILIKE",
    "IN",
    "NOT IN",
    "IS NULL",
    "IS NOT NULL"
  ],
  number: [
    "=",
    "!=",
    "<",
    "<=",
    ">",
    ">=",
    "IN",
    "NOT IN",
    "BETWEEN",
    "NOT BETWEEN",
    "IS NULL",
    "IS NOT NULL"
  ],
  boolean: ["=", "!=", "IS NULL", "IS NOT NULL"],
  date: [
    "=",
    "!=",
    "<",
    "<=",
    ">",
    ">=",
    "BETWEEN",
    "NOT BETWEEN",
    "IS NULL",
    "IS NOT NULL"
  ],
  datetime: [
    "=",
    "!=",
    "<",
    "<=",
    ">",
    ">=",
    "BETWEEN",
    "NOT BETWEEN",
    "IS NULL",
    "IS NOT NULL"
  ],
  duration: [
    "=",
    "!=",
    "<",
    "<=",
    ">",
    ">=",
    "BETWEEN",
    "NOT BETWEEN",
    "IS NULL",
    "IS NOT NULL"
  ],
  unknown: [
    "=",
    "!=",
    "LIKE",
    "NOT LIKE",
    "ILIKE",
    "NOT ILIKE",
    "IN",
    "NOT IN",
    "IS NULL",
    "IS NOT NULL"
  ]
};
const OPERATORS_WITHOUT_VALUE = /* @__PURE__ */ new Set([
  "IS NULL",
  "IS NOT NULL"
]);
const OPERATORS_WITH_LIST_VALUE = /* @__PURE__ */ new Set(["IN", "NOT IN"]);
const OPERATORS_WITH_RANGE_VALUE = /* @__PURE__ */ new Set([
  "BETWEEN",
  "NOT BETWEEN"
]);
const formatScalarValue = (value, filterType) => {
  if (value === null || value === void 0) {
    return "";
  }
  if (filterType === "date" && typeof value !== "boolean") {
    return formatDateForInput(value);
  }
  if (filterType === "datetime" && typeof value !== "boolean") {
    return formatDateTimeForInput(value);
  }
  return String(value);
};
const formatFilterValue = (value, filterType) => {
  if (value === null || value === void 0) {
    return "";
  }
  if (Array.isArray(value)) {
    if (value.length === 2) {
      return formatScalarValue(value[0], filterType);
    }
    return value.map((v) => formatScalarValue(v, filterType)).join(", ");
  }
  return formatScalarValue(value, filterType);
};
const formatFilterValue2 = (value, filterType) => {
  if (value === null || value === void 0) {
    return "";
  }
  if (Array.isArray(value) && value.length === 2) {
    return formatScalarValue(value[1], filterType);
  }
  return "";
};
const parseFilterValue = (filterType, rawValue) => {
  switch (filterType) {
    case "number":
    case "duration": {
      const parsed = Number(rawValue);
      return Number.isFinite(parsed) ? parsed : void 0;
    }
    case "boolean":
      if (rawValue === "true") return true;
      if (rawValue === "false") return false;
      return void 0;
    case "date":
    case "datetime":
      return parseDateFromInput(rawValue);
    case "unknown":
    case "string":
    default:
      return rawValue;
  }
};
const parseListValue = (filterType, rawValue) => {
  const parts = rawValue.split(",").map((s) => s.trim()).filter((s) => s !== "");
  if (parts.length === 0) {
    return void 0;
  }
  const parsed = [];
  for (const part of parts) {
    const value = parseFilterValue(filterType, part);
    if (value === void 0) {
      return void 0;
    }
    parsed.push(value);
  }
  return parsed;
};
const parseRangeValue = (filterType, rawValue1, rawValue2) => {
  const parsed1 = parseFilterValue(filterType, rawValue1);
  const parsed2 = parseFilterValue(filterType, rawValue2);
  if (parsed1 === void 0 || parsed2 === void 0) {
    return void 0;
  }
  return [parsed1, parsed2];
};
function useColumnFilter({
  columnId: columnId2,
  filterType,
  condition,
  isOpen
}) {
  const operatorOptions = OPERATORS_BY_TYPE[filterType];
  const defaultOperator = operatorOptions[0] ?? "=";
  const [operator, setOperator] = reactExports.useState(
    condition?.operator ?? defaultOperator
  );
  const [value, setValue] = reactExports.useState(
    formatFilterValue(condition?.right, filterType)
  );
  const [value2, setValue2] = reactExports.useState(
    formatFilterValue2(condition?.right, filterType)
  );
  const isValueDisabled = OPERATORS_WITHOUT_VALUE.has(operator);
  const usesListValue = OPERATORS_WITH_LIST_VALUE.has(operator);
  const usesRangeValue = OPERATORS_WITH_RANGE_VALUE.has(operator);
  const valueSelectRef = reactExports.useRef(null);
  const valueInputRef = reactExports.useRef(null);
  const prevColumnIdRef = reactExports.useRef(columnId2);
  reactExports.useEffect(() => {
    const columnChanged = prevColumnIdRef.current !== columnId2;
    prevColumnIdRef.current = columnId2;
    if (!isOpen || columnChanged) {
      setOperator(condition?.operator ?? defaultOperator);
      setValue(formatFilterValue(condition?.right, filterType));
      setValue2(formatFilterValue2(condition?.right, filterType));
    }
  }, [condition, defaultOperator, filterType, isOpen, columnId2, setValue]);
  reactExports.useEffect(() => {
    if (!isOpen || isValueDisabled) {
      return;
    }
    const timer = window.setTimeout(() => {
      if (filterType === "boolean") {
        valueSelectRef.current?.focus();
      } else {
        valueInputRef.current?.focus();
      }
    }, 0);
    return () => window.clearTimeout(timer);
  }, [filterType, isOpen, isValueDisabled]);
  const buildCondition = reactExports.useCallback(
    (operator2, value3, value22) => {
      if (OPERATORS_WITHOUT_VALUE.has(operator2)) {
        return ConditionBuilder.simple(columnId2, operator2, null);
      }
      if (value3.trim() === "") {
        return null;
      }
      if (OPERATORS_WITH_LIST_VALUE.has(operator2)) {
        const parsed2 = parseListValue(filterType, value3);
        if (parsed2 === void 0) {
          return void 0;
        }
        return ConditionBuilder.simple(columnId2, operator2, parsed2);
      }
      if (OPERATORS_WITH_RANGE_VALUE.has(operator2)) {
        if (!value22 || value22.trim() === "") {
          return null;
        }
        const parsed2 = parseRangeValue(filterType, value3, value22);
        if (parsed2 === void 0) {
          return void 0;
        }
        return ConditionBuilder.simple(columnId2, operator2, parsed2);
      }
      const parsed = parseFilterValue(filterType, value3);
      if (parsed === void 0) {
        return void 0;
      }
      if (operator2 === "LIKE" || operator2 === "NOT LIKE" || operator2 === "ILIKE" || operator2 === "NOT ILIKE") {
        let modified = String(parsed);
        if (!modified.includes("%")) {
          modified = `%${modified}%`;
        }
        return ConditionBuilder.simple(columnId2, operator2, modified);
      } else {
        return ConditionBuilder.simple(columnId2, operator2, parsed);
      }
    },
    [columnId2, filterType]
  );
  return {
    operator,
    setOperator,
    value,
    setValue,
    value2,
    setValue2,
    operatorOptions,
    usesValue: isValueDisabled,
    usesListValue,
    usesRangeValue,
    buildCondition
  };
}
function useColumnFilterPopover({
  columnId: columnId2,
  filterType,
  condition,
  onChange
}) {
  const [isOpen, setIsOpen] = reactExports.useState(false);
  const cancelRef = reactExports.useRef(false);
  const prevOpenRef = reactExports.useRef(false);
  const {
    operator,
    setOperator,
    value,
    setValue,
    value2,
    setValue2,
    operatorOptions,
    usesValue: isValueDisabled,
    usesRangeValue: isRangeOperator,
    buildCondition
  } = useColumnFilter({
    columnId: columnId2,
    filterType,
    condition,
    isOpen
  });
  const cancelAndClose = reactExports.useCallback(() => {
    cancelRef.current = true;
    setIsOpen(false);
  }, []);
  const commitAndClose = reactExports.useCallback(() => {
    const nextCondition = buildCondition(operator, value, value2);
    if (nextCondition === void 0) {
      return;
    }
    setIsOpen(false);
  }, [buildCondition, operator, value, value2]);
  reactExports.useEffect(() => {
    if (prevOpenRef.current && !isOpen) {
      if (cancelRef.current) {
        cancelRef.current = false;
      } else {
        const nextCondition = buildCondition(operator, value, value2);
        if (nextCondition !== void 0) {
          onChange(nextCondition);
        }
      }
    }
    prevOpenRef.current = isOpen;
  }, [buildCondition, isOpen, onChange, operator, value, value2]);
  return {
    isOpen,
    setIsOpen,
    operator,
    setOperator,
    value,
    setValue,
    value2,
    setValue2,
    operatorOptions,
    isValueDisabled,
    isRangeOperator,
    commitAndClose,
    cancelAndClose
  };
}
function useAddFilterPopover({
  columns,
  filters,
  onAddFilter,
  onFilterColumnChange
}) {
  const [isOpen, setIsOpen] = reactExports.useState(false);
  const [selectedColumnId, setSelectedColumnId] = reactExports.useState(null);
  const prevOpenRef = reactExports.useRef(false);
  const selectedColumn = selectedColumnId ? columns.find((c) => c.id === selectedColumnId) : null;
  const filterType = selectedColumn?.filterType ?? "string";
  const existingFilter = selectedColumnId ? filters[selectedColumnId] : null;
  const {
    operator,
    setOperator,
    value,
    setValue,
    value2,
    setValue2,
    operatorOptions,
    usesValue: isValueDisabled,
    usesRangeValue: isRangeOperator,
    buildCondition
  } = useColumnFilter({
    columnId: selectedColumnId ?? "",
    filterType,
    condition: existingFilter?.condition ?? null,
    isOpen
  });
  reactExports.useEffect(() => {
    if (isOpen && !prevOpenRef.current) {
      setSelectedColumnId(null);
    }
    prevOpenRef.current = isOpen;
  }, [isOpen]);
  reactExports.useEffect(() => {
    if (prevOpenRef.current && !isOpen) {
      onFilterColumnChange?.(null);
    }
  }, [isOpen, onFilterColumnChange]);
  const handleColumnChange = reactExports.useCallback(
    (newColumnId) => {
      setSelectedColumnId(newColumnId || null);
      if (newColumnId) {
        onFilterColumnChange?.(newColumnId);
      }
    },
    [onFilterColumnChange]
  );
  const commitAndClose = reactExports.useCallback(() => {
    if (!selectedColumnId) return;
    const condition = buildCondition(operator, value, value2);
    if (condition === void 0) return;
    onAddFilter({ columnId: selectedColumnId, filterType, condition });
    setIsOpen(false);
  }, [
    selectedColumnId,
    buildCondition,
    operator,
    value,
    value2,
    onAddFilter,
    filterType
  ]);
  const cancelAndClose = reactExports.useCallback(() => setIsOpen(false), []);
  return {
    isOpen,
    setIsOpen,
    selectedColumnId,
    columns,
    filterType,
    operator,
    setOperator,
    operatorOptions,
    value,
    setValue,
    value2,
    setValue2,
    isValueDisabled,
    isRangeOperator,
    handleColumnChange,
    commitAndClose,
    cancelAndClose
  };
}
const container = "_container_1ljjt_1";
const filterBar = "_filterBar_1ljjt_11";
const filterLabel = "_filterLabel_1ljjt_15";
const actionButtons = "_actionButtons_1ljjt_24";
const actionButton = "_actionButton_1ljjt_24";
const chipButton = "_chipButton_1ljjt_46";
const sep = "_sep_1ljjt_51";
const filterChip = "_filterChip_1ljjt_60";
const columnsButton = "_columnsButton_1ljjt_64";
const styles$2 = {
  container,
  filterBar,
  filterLabel,
  actionButtons,
  actionButton,
  chipButton,
  sep,
  filterChip,
  columnsButton
};
const AddFilterButton = ({
  idPrefix,
  popoverState,
  suggestions = []
}) => {
  const chipRef = reactExports.useRef(null);
  const {
    isOpen,
    setIsOpen,
    selectedColumnId,
    columns,
    filterType,
    operator,
    setOperator,
    operatorOptions,
    value,
    setValue,
    value2,
    setValue2,
    isValueDisabled,
    isRangeOperator,
    handleColumnChange,
    commitAndClose,
    cancelAndClose
  } = popoverState;
  return /* @__PURE__ */ jsxRuntimeExports.jsxs(jsxRuntimeExports.Fragment, { children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx(
      Chip,
      {
        ref: chipRef,
        icon: ApplicationIcons.add,
        value: "Add",
        title: "Add a new filter",
        className: clsx(styles$2.filterChip, "text-size-smallest"),
        onClick: () => setIsOpen(true)
      }
    ),
    /* @__PURE__ */ jsxRuntimeExports.jsx(
      PopOver,
      {
        id: `${idPrefix}-add-filter-editor`,
        isOpen,
        setIsOpen,
        positionEl: chipRef.current,
        placement: "bottom-start",
        showArrow: true,
        hoverDelay: -1,
        closeOnMouseLeave: false,
        styles: {
          padding: "0.4rem",
          backgroundColor: "var(--bs-light)"
        },
        children: /* @__PURE__ */ jsxRuntimeExports.jsx(
          ColumnFilterEditor,
          {
            mode: "add",
            columnId: selectedColumnId ?? "",
            filterType,
            operator,
            operatorOptions,
            rawValue: value,
            rawValue2: value2,
            isValueDisabled,
            isRangeOperator,
            onOperatorChange: setOperator,
            onValueChange: setValue,
            onValue2Change: setValue2,
            onCommit: commitAndClose,
            onCancel: cancelAndClose,
            suggestions,
            columns,
            onColumnChange: handleColumnChange
          }
        )
      }
    )
  ] });
};
const chipGroup = "_chipGroup_1de1s_1";
const styles$1 = {
  chipGroup
};
const ChipGroup = ({ className, children }) => {
  return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx(styles$1.chipGroup, className), children });
};
const ColumnPickerButton = ({
  children
}) => {
  const buttonRef = reactExports.useRef(null);
  const [isOpen, setIsOpen] = reactExports.useState(false);
  return /* @__PURE__ */ jsxRuntimeExports.jsxs(jsxRuntimeExports.Fragment, { children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx(
      ToolButton,
      {
        ref: buttonRef,
        icon: ApplicationIcons.checkbox.checked,
        label: "Choose columns",
        title: "Choose columns",
        latched: isOpen,
        onClick: () => setIsOpen(!isOpen),
        subtle: true,
        className: clsx("text-size-smallest", styles$2.columnsButton)
      }
    ),
    children({
      // eslint-disable-next-line react-hooks/refs -- positionEl accepts null; PopOver/Popper handles this in effects and updates when ref is populated
      positionEl: buttonRef.current,
      isOpen,
      setIsOpen
    })
  ] });
};
const columnList = "_columnList_1wz3s_1";
const row = "_row_1wz3s_9";
const links = "_links_1wz3s_23";
const selected = "_selected_1wz3s_41";
const styles = {
  columnList,
  row,
  links,
  selected
};
const ColumnsPopover = ({
  positionEl,
  isOpen,
  setIsOpen,
  columns,
  visibleColumns,
  defaultVisibleColumns,
  onVisibleColumnsChange,
  popoverId = "columns-popover"
}) => {
  const isDefaultSelection = reactExports.useMemo(
    () => visibleColumns.length === defaultVisibleColumns.length && visibleColumns.every((col) => defaultVisibleColumns.includes(col)),
    [visibleColumns, defaultVisibleColumns]
  );
  const isAllSelection = reactExports.useMemo(
    () => visibleColumns.length === columns.length,
    [visibleColumns, columns]
  );
  const setDefaultSelection = reactExports.useCallback(() => {
    onVisibleColumnsChange(defaultVisibleColumns);
  }, [onVisibleColumnsChange, defaultVisibleColumns]);
  const setAllSelection = reactExports.useCallback(() => {
    onVisibleColumnsChange(columns.map((c) => c.id));
  }, [onVisibleColumnsChange, columns]);
  const toggleColumn = reactExports.useCallback(
    (columnId2, show) => {
      if (show && !visibleColumns.includes(columnId2)) {
        onVisibleColumnsChange([...visibleColumns, columnId2]);
      } else if (!show) {
        onVisibleColumnsChange(visibleColumns.filter((c) => c !== columnId2));
      }
    },
    [visibleColumns, onVisibleColumnsChange]
  );
  return /* @__PURE__ */ jsxRuntimeExports.jsxs(
    PopOver,
    {
      id: popoverId,
      positionEl,
      isOpen,
      setIsOpen,
      placement: "bottom-end",
      hoverDelay: -1,
      children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: clsx(styles.links, "text-size-smaller"), children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "a",
            {
              className: clsx(
                styles.link,
                isDefaultSelection ? styles.selected : void 0
              ),
              onClick: () => setDefaultSelection(),
              children: "Default"
            }
          ),
          "|",
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "a",
            {
              className: clsx(
                styles.link,
                isAllSelection ? styles.selected : void 0
              ),
              onClick: () => setAllSelection(),
              children: "All"
            }
          )
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx(styles.columnList, "text-size-smaller"), children: columns.map((column) => /* @__PURE__ */ jsxRuntimeExports.jsxs(
          "div",
          {
            className: clsx(styles.row),
            title: [column.id, column.headerTitle].filter(Boolean).join("\n"),
            onClick: () => {
              toggleColumn(column.id, !visibleColumns.includes(column.id));
            },
            children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx(
                "input",
                {
                  type: "checkbox",
                  checked: visibleColumns.includes(column.id),
                  onChange: (e) => {
                    toggleColumn(column.id, e.target.checked);
                  }
                }
              ),
              column.label
            ]
          },
          column.id
        )) })
      ]
    }
  );
};
const kCopyCodeDescriptors = [
  { label: "Code (Python)", value: "python" },
  { label: "Filter (SQL)", value: "filter" }
];
const FilterBar = ({
  filters,
  onFilterChange,
  onRemoveFilter,
  filterCodeValues,
  filterSuggestions = [],
  onFilterColumnChange,
  popoverIdPrefix = "filter",
  addFilterPopoverState,
  columns,
  visibleColumns,
  defaultVisibleColumns,
  onVisibleColumnsChange
}) => {
  const [editingColumnId, setEditingColumnId] = reactExports.useState(null);
  const chipRefs = reactExports.useRef({});
  const editingFilter = editingColumnId ? filters[editingColumnId] : null;
  const handleFilterChange = reactExports.useCallback(
    (condition) => {
      if (!editingColumnId) return;
      onFilterChange(editingColumnId, condition);
    },
    [editingColumnId, onFilterChange]
  );
  const {
    isOpen: isEditorOpen,
    setIsOpen: setIsEditorOpen,
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
    columnId: editingColumnId ?? "",
    filterType: editingFilter?.filterType ?? "string",
    condition: editingFilter?.condition ?? null,
    onChange: handleFilterChange
  });
  const editFilter = reactExports.useCallback(
    (columnId2) => () => {
      setEditingColumnId(columnId2);
      setIsEditorOpen(true);
      onFilterColumnChange?.(columnId2);
    },
    [setIsEditorOpen, onFilterColumnChange]
  );
  const handleEditorOpenChange = reactExports.useCallback(
    (open) => {
      setIsEditorOpen(open);
      if (!open) {
        onFilterColumnChange?.(null);
      }
    },
    [setIsEditorOpen, onFilterColumnChange]
  );
  const filterEntries = Object.values(filters);
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles$2.container, children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx(
      "div",
      {
        className: clsx(
          "text-style-label",
          "text-style-secondary",
          "text-size-smallest",
          styles$2.filterLabel
        ),
        children: "Filter:"
      }
    ),
    /* @__PURE__ */ jsxRuntimeExports.jsxs(ChipGroup, { className: styles$2.filterBar, children: [
      filterEntries.length > 0 ? filterEntries.map((filter) => {
        if (!filter || !filter.condition) {
          return null;
        }
        return /* @__PURE__ */ jsxRuntimeExports.jsx(
          Chip,
          {
            ref: (el) => {
              chipRefs.current[filter.columnId] = el;
            },
            label: filter.columnId,
            value: formatFilterCondition(filter.condition),
            title: `Edit ${filter.columnId} filter`,
            closeTitle: "Remove filter",
            className: clsx(styles$2.filterChip, "text-size-smallest"),
            onClose: () => {
              onRemoveFilter(filter.columnId);
            },
            onClick: editFilter(filter.columnId)
          },
          filter.columnId
        );
      }) : null,
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        AddFilterButton,
        {
          idPrefix: popoverIdPrefix,
          popoverState: addFilterPopoverState,
          suggestions: filterSuggestions
        }
      )
    ] }),
    editingColumnId && editingFilter && /* @__PURE__ */ jsxRuntimeExports.jsx(
      PopOver,
      {
        id: `${popoverIdPrefix}-editor-${editingColumnId}`,
        isOpen: isEditorOpen,
        setIsOpen: handleEditorOpenChange,
        positionEl: chipRefs.current[editingColumnId] ?? null,
        placement: "bottom-start",
        showArrow: true,
        hoverDelay: -1,
        closeOnMouseLeave: false,
        styles: {
          padding: "0.4rem",
          backgroundColor: "var(--bs-light)"
        },
        children: /* @__PURE__ */ jsxRuntimeExports.jsx(
          ColumnFilterEditor,
          {
            columnId: editingColumnId,
            filterType: editingFilter.filterType,
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
            suggestions: filterSuggestions
          }
        )
      }
    ),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: clsx(styles$2.actionButtons), children: [
      filterCodeValues !== void 0 && /* @__PURE__ */ jsxRuntimeExports.jsx(CopyQueryButton, { itemValues: filterCodeValues }),
      columns && onVisibleColumnsChange && /* @__PURE__ */ jsxRuntimeExports.jsxs(jsxRuntimeExports.Fragment, { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles$2.sep }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(ColumnPickerButton, { children: ({ positionEl, isOpen, setIsOpen }) => /* @__PURE__ */ jsxRuntimeExports.jsx(
          ColumnsPopover,
          {
            positionEl,
            isOpen,
            setIsOpen,
            columns,
            visibleColumns: visibleColumns ?? defaultVisibleColumns ?? [],
            defaultVisibleColumns: defaultVisibleColumns ?? [],
            onVisibleColumnsChange,
            popoverId: `${popoverIdPrefix}-columns`
          }
        ) })
      ] })
    ] })
  ] });
};
const CopyQueryButton = ({
  itemValues
}) => {
  const [icon, setIcon] = reactExports.useState(ApplicationIcons.copy);
  const items = kCopyCodeDescriptors.reduce(
    (acc, desc) => {
      acc[desc.label] = () => {
        const text = itemValues ? itemValues[desc.value] : "";
        if (!text) {
          return;
        }
        void navigator.clipboard.writeText(text);
        setIcon(ApplicationIcons.confirm);
        setTimeout(() => {
          setIcon(ApplicationIcons.copy);
        }, 1250);
      };
      return acc;
    },
    {}
  );
  return /* @__PURE__ */ jsxRuntimeExports.jsx(
    ToolDropdownButton,
    {
      label: "Copy",
      icon,
      title: "Copy Filter",
      className: clsx(styles$2.actionButton, styles$2.chipButton, styles$2.right),
      disabled: Object.keys(itemValues || []).length === 0,
      dropdownAlign: "right",
      dropdownClassName: "text-size-smallest",
      items
    },
    "query-copy"
  );
};
const formatRepresentativeType = (value) => {
  if (value === null) {
    return "NULL";
  } else if (Array.isArray(value)) {
    return `[${value.map((v) => formatRepresentativeType(v)).join(", ")}]`;
  } else if (typeof value === "object") {
    return "{...}";
  } else if (typeof value === "string") {
    return `'${value}'`;
  } else {
    return String(value);
  }
};
const formatFilterCondition = (condition) => {
  const { operator, right } = condition;
  if ((operator === "BETWEEN" || operator === "NOT BETWEEN") && Array.isArray(right) && right.length === 2) {
    const v1 = formatRepresentativeType(right[0]);
    const v2 = formatRepresentativeType(right[1]);
    return `${operator} ${v1} AND ${v2}`;
  }
  if ((operator === "IN" || operator === "NOT IN") && Array.isArray(right)) {
    const values = right.map((v) => formatRepresentativeType(v)).join(", ");
    return `${operator} (${values})`;
  }
  if (operator === "IS NULL" || operator === "IS NOT NULL") {
    return operator;
  }
  return `${operator} ${formatRepresentativeType(right)}`;
};
function createFilterBarHandlers(setTableState, defaultVisibleColumns) {
  const handleFilterChange = (columnId2, condition) => {
    setTableState((prevState) => {
      const newFilters = { ...prevState.columnFilters };
      if (condition === null) {
        delete newFilters[columnId2];
      } else {
        const existingFilter = newFilters[columnId2];
        if (existingFilter) {
          newFilters[columnId2] = {
            ...existingFilter,
            condition
          };
        }
      }
      return {
        ...prevState,
        columnFilters: newFilters
      };
    });
  };
  const removeFilter = (column) => {
    setTableState((prevState) => {
      const newFilters = { ...prevState.columnFilters };
      delete newFilters[column];
      return {
        ...prevState,
        columnFilters: newFilters
      };
    });
  };
  const handleAddFilter = (filter) => {
    setTableState((prevState) => {
      const columnKey = filter.columnId;
      const currentVisibleColumns = prevState.visibleColumns ?? [...defaultVisibleColumns];
      const needsColumnVisible = !currentVisibleColumns.includes(columnKey);
      const columnOrder = prevState.columnOrder;
      const needsColumnOrder = columnOrder.length > 0 && !columnOrder.includes(columnKey);
      return {
        ...prevState,
        columnFilters: {
          ...prevState.columnFilters,
          [filter.columnId]: filter
        },
        // Add the column to visible columns if it's not already there
        ...needsColumnVisible && {
          visibleColumns: [...currentVisibleColumns, columnKey]
        },
        // Add the column to column order if it's not already there
        ...needsColumnOrder && {
          columnOrder: [...columnOrder, columnKey]
        }
      };
    });
  };
  return {
    handleFilterChange,
    removeFilter,
    handleAddFilter
  };
}
function useFilterBarHandlers({
  setTableState,
  defaultVisibleColumns
}) {
  const handlers = reactExports.useMemo(
    () => createFilterBarHandlers(setTableState, defaultVisibleColumns),
    [setTableState, defaultVisibleColumns]
  );
  const handleFilterChange = reactExports.useCallback(
    (columnId2, condition) => {
      handlers.handleFilterChange(columnId2, condition);
    },
    [handlers]
  );
  const removeFilter = reactExports.useCallback(
    (column) => {
      handlers.removeFilter(column);
    },
    [handlers]
  );
  const handleAddFilter = reactExports.useCallback(
    (filter) => {
      handlers.handleAddFilter(filter);
    },
    [handlers]
  );
  return {
    handleFilterChange,
    removeFilter,
    handleAddFilter
  };
}
export {
  ColumnFilterButton as C,
  FilterBar as F,
  useAddFilterPopover as a,
  useColumnFilterPopover as b,
  ColumnFilterEditor as c,
  useFilterBarHandlers as u
};
//# sourceMappingURL=useFilterBarHandlers.js.map
