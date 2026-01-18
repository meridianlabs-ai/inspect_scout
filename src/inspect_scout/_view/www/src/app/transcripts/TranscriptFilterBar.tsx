import { clsx } from "clsx";
import { FC, useCallback, useRef, useState } from "react";

import { ScalarValue } from "../../api/api";
import { ApplicationIcons } from "../../components/icons";
import { PopOver } from "../../components/PopOver";
import { ToolDropdownButton } from "../../components/ToolDropdownButton";
import type { SimpleCondition } from "../../query/types";
import { ColumnFilter, useStore } from "../../state/store";
import type { TranscriptInfo } from "../../types/api-types";
import { Chip } from "../components/Chip";
import { ChipGroup } from "../components/ChipGroup";

import { ColumnFilterEditor } from "./columnFilter/ColumnFilterEditor";
import { useAddFilterPopover } from "./columnFilter/useAddFilterPopover";
import { useColumnFilterPopover } from "./columnFilter/useColumnFilterPopover";
import { DEFAULT_VISIBLE_COLUMNS, getFilterTypeForColumn } from "./columns";
import { TranscriptColumnsButton } from "./TranscriptColumnsButton";
import { TranscriptColumnsPopover } from "./TranscriptColumnsPopover";
import styles from "./TranscriptFilterBar.module.css";

const kCopyCodeDescriptors = [
  { label: "Code (Python)", value: "python" },
  { label: "Filter (SQL)", value: "filter" },
];

export const TranscriptFilterBar: FC<{
  filterCodeValues?: Record<string, string>;
  filterSuggestions?: ScalarValue[];
  onFilterColumnChange?: (columnId: string | null) => void;
}> = ({ filterCodeValues, filterSuggestions = [], onFilterColumnChange }) => {
  // Transcript Filter State
  const filters = useStore(
    (state) => state.transcriptsTableState.columnFilters
  );
  const setTranscriptsTableState = useStore(
    (state) => state.setTranscriptsTableState
  );

  const removeFilter = useCallback(
    (column: string) => {
      setTranscriptsTableState((prevState) => {
        const newFilters = { ...prevState.columnFilters };
        delete newFilters[column];
        return {
          ...prevState,
          columnFilters: newFilters,
        };
      });
    },
    [setTranscriptsTableState]
  );

  // Column picker state
  const [showColumnPicker, setShowColumnPicker] = useState(false);
  const columnButtonRef = useRef<HTMLButtonElement>(null);

  // Filter editing state
  const [editingColumnId, setEditingColumnId] = useState<string | null>(null);
  const chipRefs = useRef<Record<string, HTMLDivElement | null>>({});
  const addFilterChipRef = useRef<HTMLDivElement | null>(null);

  const editingFilter = editingColumnId ? filters[editingColumnId] : null;

  // Add filter handler - also ensures the filtered column is visible
  const handleAddFilter = useCallback(
    (filter: ColumnFilter) => {
      setTranscriptsTableState((prevState) => {
        const columnKey = filter.columnId as keyof TranscriptInfo;

        // Use default visible columns if not set in state
        const currentVisibleColumns =
          prevState.visibleColumns ?? DEFAULT_VISIBLE_COLUMNS;

        // Check if we need to add this column to visible columns
        const needsColumnVisible = !currentVisibleColumns.includes(columnKey);

        // Check if we need to add this column to column order
        const needsColumnOrder =
          prevState.columnOrder.length > 0 &&
          !prevState.columnOrder.includes(columnKey);

        return {
          ...prevState,
          columnFilters: {
            ...prevState.columnFilters,
            [filter.columnId]: filter,
          },
          // Add the column to visible columns if it's not already there
          ...(needsColumnVisible && {
            visibleColumns: [...currentVisibleColumns, columnKey],
          }),
          // Add the column to column order if it's not already there
          ...(needsColumnOrder && {
            columnOrder: [...prevState.columnOrder, columnKey],
          }),
        };
      });
    },
    [setTranscriptsTableState]
  );

  // Add filter popover
  const {
    isOpen: isAddFilterOpen,
    setIsOpen: setIsAddFilterOpen,
    selectedColumnId: addFilterColumnId,
    availableColumns,
    operator: addFilterOperator,
    setOperator: setAddFilterOperator,
    operatorOptions: addFilterOperatorOptions,
    value: addFilterValue,
    setValue: setAddFilterValue,
    value2: addFilterValue2,
    setValue2: setAddFilterValue2,
    isValueDisabled: isAddFilterValueDisabled,
    isRangeOperator: isAddFilterRangeOperator,
    commitAndClose: commitAddFilterAndClose,
    cancelAndClose: cancelAddFilterAndClose,
    handleColumnChange: handleAddFilterColumnChange,
  } = useAddFilterPopover({
    filters,
    onAddFilter: handleAddFilter,
    onFilterColumnChange,
  });

  // Get filter type for add filter mode
  const addFilterType = addFilterColumnId
    ? getFilterTypeForColumn(addFilterColumnId)
    : "string";

  const handleFilterChange = useCallback(
    (condition: SimpleCondition | null) => {
      if (!editingColumnId) return;

      setTranscriptsTableState((prevState) => {
        const newFilters = { ...prevState.columnFilters };
        if (condition === null) {
          delete newFilters[editingColumnId];
        } else {
          const existingFilter = newFilters[editingColumnId];
          if (existingFilter) {
            newFilters[editingColumnId] = {
              ...existingFilter,
              condition,
            };
          }
        }
        return {
          ...prevState,
          columnFilters: newFilters,
        };
      });
    },
    [editingColumnId, setTranscriptsTableState]
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
    cancelAndClose,
  } = useColumnFilterPopover({
    columnId: editingColumnId ?? "",
    filterType: editingFilter?.filterType ?? "string",
    condition: editingFilter?.condition ?? null,
    onChange: handleFilterChange,
  });

  const editFilter = useCallback(
    (columnId: string) => () => {
      setEditingColumnId(columnId);
      setIsEditorOpen(true);
      onFilterColumnChange?.(columnId);
    },
    [setIsEditorOpen, onFilterColumnChange]
  );

  // Notify parent when editor closes
  const handleEditorOpenChange = useCallback(
    (open: boolean) => {
      setIsEditorOpen(open);
      if (!open) {
        onFilterColumnChange?.(null);
      }
    },
    [setIsEditorOpen, onFilterColumnChange]
  );

  const filterEntries = Object.values(filters);

  return (
    <div className={styles.container}>
      <div
        className={clsx(
          "text-style-label",
          "text-style-secondary",
          "text-size-smallest",
          styles.filterLabel
        )}
      >
        Filter:
      </div>
      <ChipGroup className={styles.filterBar}>
        {filterEntries.length > 0
          ? filterEntries.map((filter) => {
              if (!filter || !filter.condition) {
                return null;
              }
              return (
                <Chip
                  key={filter.columnId}
                  ref={(el) => {
                    chipRefs.current[filter.columnId] = el;
                  }}
                  label={filter.columnId}
                  value={formatFilterCondition(filter.condition)}
                  title={`Edit ${filter.columnId} filter`}
                  closeTitle="Remove filter"
                  className={clsx(styles.filterChip, "text-size-smallestest")}
                  onClose={() => {
                    removeFilter(filter.columnId);
                  }}
                  onClick={editFilter(filter.columnId)}
                />
              );
            })
          : null}
        {/* Add Filter chip */}
        <Chip
          ref={addFilterChipRef}
          icon={ApplicationIcons.changes.add}
          value="Add"
          title="Add a new filter"
          className={clsx(styles.filterChip, "text-size-smallestest")}
          onClick={() => setIsAddFilterOpen(true)}
        />
      </ChipGroup>
      {filterEntries.length > 0 && (
        <>
          <CopyQueryButton itemValues={filterCodeValues} />
          <div className={styles.sep}></div>
        </>
      )}

      {/* Edit filter popover */}
      {editingColumnId && editingFilter && (
        <PopOver
          id={`transcript-filter-editor-${editingColumnId}`}
          isOpen={isEditorOpen}
          setIsOpen={handleEditorOpenChange}
          positionEl={chipRefs.current[editingColumnId] ?? null}
          placement="bottom-start"
          showArrow={true}
          hoverDelay={-1}
          closeOnMouseLeave={false}
          styles={{
            padding: "0.4rem",
            backgroundColor: "var(--bs-light)",
          }}
        >
          <ColumnFilterEditor
            columnId={editingColumnId}
            filterType={editingFilter.filterType}
            operator={operator}
            operatorOptions={operatorOptions}
            rawValue={rawValue}
            rawValue2={rawValue2}
            isValueDisabled={isValueDisabled}
            isRangeOperator={isRangeOperator}
            onOperatorChange={setOperator}
            onValueChange={setRawValue}
            onValue2Change={setRawValue2}
            onCommit={commitAndClose}
            onCancel={cancelAndClose}
            suggestions={filterSuggestions}
          />
        </PopOver>
      )}

      {/* Add filter popover */}
      <PopOver
        id="transcript-add-filter-editor"
        isOpen={isAddFilterOpen}
        setIsOpen={setIsAddFilterOpen}
        positionEl={addFilterChipRef.current}
        placement="bottom-start"
        showArrow={true}
        hoverDelay={-1}
        closeOnMouseLeave={false}
        styles={{
          padding: "0.4rem",
          backgroundColor: "var(--bs-light)",
        }}
      >
        <ColumnFilterEditor
          mode="add"
          columnId={addFilterColumnId ?? ""}
          filterType={addFilterType}
          operator={addFilterOperator}
          operatorOptions={addFilterOperatorOptions}
          rawValue={addFilterValue}
          rawValue2={addFilterValue2}
          isValueDisabled={isAddFilterValueDisabled}
          isRangeOperator={isAddFilterRangeOperator}
          onOperatorChange={setAddFilterOperator}
          onValueChange={setAddFilterValue}
          onValue2Change={setAddFilterValue2}
          onCommit={commitAddFilterAndClose}
          onCancel={cancelAddFilterAndClose}
          suggestions={filterSuggestions}
          availableColumns={availableColumns}
          onColumnChange={handleAddFilterColumnChange}
        />
      </PopOver>
      <div className={clsx(styles.actionButtons)}>
        <TranscriptColumnsButton
          ref={columnButtonRef}
          isOpen={showColumnPicker}
          onClick={() => setShowColumnPicker(!showColumnPicker)}
        />
        <TranscriptColumnsPopover
          positionEl={columnButtonRef.current}
          isOpen={showColumnPicker}
          setIsOpen={setShowColumnPicker}
        />
      </div>
    </div>
  );
};

const CopyQueryButton: FC<{ itemValues?: Record<string, string> }> = ({
  itemValues,
}) => {
  const [icon, setIcon] = useState<string>(ApplicationIcons.copy);

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
    {} as Record<string, () => void>
  );

  return (
    <ToolDropdownButton
      key="query-copy"
      label="Copy"
      icon={icon}
      title="Copy Filter"
      className={clsx(styles.actionButton, styles.chipButton)}
      disabled={Object.keys(itemValues || []).length === 0}
      dropdownAlign="right"
      dropdownClassName={"text-size-smallest"}
      items={items}
    />
  );
};

const formatRepresentativeType = (value: unknown): string => {
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

/**
 * Formats a filter condition for display in a chip.
 * Handles special formatting for BETWEEN, IN, and other operators.
 */
const formatFilterCondition = (condition: SimpleCondition): string => {
  const { operator, right } = condition;

  // BETWEEN / NOT BETWEEN: show as "BETWEEN value1 AND value2"
  if (
    (operator === "BETWEEN" || operator === "NOT BETWEEN") &&
    Array.isArray(right) &&
    right.length === 2
  ) {
    const v1 = formatRepresentativeType(right[0]);
    const v2 = formatRepresentativeType(right[1]);
    return `${operator} ${v1} AND ${v2}`;
  }

  // IN / NOT IN: show as "IN (value1, value2, ...)"
  if (
    (operator === "IN" || operator === "NOT IN") &&
    Array.isArray(right)
  ) {
    const values = right.map((v) => formatRepresentativeType(v)).join(", ");
    return `${operator} (${values})`;
  }

  // IS NULL / IS NOT NULL: no value needed
  if (operator === "IS NULL" || operator === "IS NOT NULL") {
    return operator;
  }

  // Default: "operator value"
  return `${operator} ${formatRepresentativeType(right)}`;
};
