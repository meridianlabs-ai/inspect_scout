import { clsx } from "clsx";
import { FC, useCallback, useRef, useState } from "react";

import { ScalarValue } from "../../api/api";
import { ApplicationIcons } from "../../components/icons";
import { PopOver } from "../../components/PopOver";
import { ToolDropdownButton } from "../../components/ToolDropdownButton";
import type { SimpleCondition } from "../../query/types";
import type { ColumnFilter } from "../../state/store";

import { AddFilterButton, type AddFilterPopoverState } from "./AddFilterButton";
import { Chip } from "./Chip";
import { ChipGroup } from "./ChipGroup";
import {
  ColumnFilterEditor,
  useColumnFilterPopover,
  type AvailableColumn,
} from "./columnFilter";
import { ColumnPickerButton } from "./ColumnPickerButton";
import { ColumnsPopover, type ColumnInfo } from "./ColumnsPopover";
import styles from "./FilterBar.module.css";

const kCopyCodeDescriptors = [
  { label: "Code (Python)", value: "python" },
  { label: "Filter (SQL)", value: "filter" },
];

export interface FilterBarProps {
  /** Current column filters */
  filters: Record<string, ColumnFilter>;
  /** Callback when a filter condition is changed */
  onFilterChange: (columnId: string, condition: SimpleCondition | null) => void;
  /** Callback when a filter is removed */
  onRemoveFilter: (columnId: string) => void;
  /** Optional code representations for copy functionality */
  filterCodeValues?: Record<string, string>;
  /** Autocomplete suggestions for filter values */
  filterSuggestions?: ScalarValue[];
  /** Callback when filter column selection changes (for fetching suggestions) */
  onFilterColumnChange?: (columnId: string | null) => void;
  /** Unique ID prefix for popovers */
  popoverIdPrefix?: string;

  // Add filter button config
  /** Popover state from useAddFilterPopover hook */
  addFilterPopoverState: AddFilterPopoverState;

  // Column picker config (optional - omit to hide)
  /** Column definitions for the picker */
  columns?: ColumnInfo[];
  /** Currently visible column IDs */
  visibleColumns?: string[];
  /** Default visible column IDs */
  defaultVisibleColumns?: string[];
  /** Callback when visible columns change */
  onVisibleColumnsChange?: (columns: string[]) => void;
}

export const FilterBar: FC<FilterBarProps> = ({
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
  onVisibleColumnsChange,
}) => {
  // Filter editing state
  const [editingColumnId, setEditingColumnId] = useState<string | null>(null);
  const chipRefs = useRef<Record<string, HTMLDivElement | null>>({});

  const editingFilter = editingColumnId ? filters[editingColumnId] : null;

  const handleFilterChange = useCallback(
    (condition: SimpleCondition | null) => {
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
                  className={clsx(styles.filterChip, "text-size-smallest")}
                  onClose={() => {
                    onRemoveFilter(filter.columnId);
                  }}
                  onClick={editFilter(filter.columnId)}
                />
              );
            })
          : null}
        {/* Add Filter Button - rendered internally */}
        <AddFilterButton
          idPrefix={popoverIdPrefix}
          popoverState={addFilterPopoverState}
          suggestions={filterSuggestions}
        />
      </ChipGroup>

      {/* Edit filter popover */}
      {editingColumnId && editingFilter && (
        <PopOver
          id={`${popoverIdPrefix}-editor-${editingColumnId}`}
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

      <div className={clsx(styles.actionButtons)}>
        {filterCodeValues !== undefined && (
          <CopyQueryButton itemValues={filterCodeValues} />
        )}
        {/* Column Picker - rendered if columns and handler provided */}
        {columns && onVisibleColumnsChange && (
          <>
            <div className={styles.sep}></div>
            <ColumnPickerButton>
              {({ positionEl, isOpen, setIsOpen }) => (
                <ColumnsPopover
                  positionEl={positionEl}
                  isOpen={isOpen}
                  setIsOpen={setIsOpen}
                  columns={columns}
                  visibleColumns={visibleColumns ?? defaultVisibleColumns ?? []}
                  defaultVisibleColumns={defaultVisibleColumns ?? []}
                  onVisibleColumnsChange={onVisibleColumnsChange}
                  popoverId={`${popoverIdPrefix}-columns`}
                />
              )}
            </ColumnPickerButton>
          </>
        )}
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
      className={clsx(styles.actionButton, styles.chipButton, styles.right)}
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
  if ((operator === "IN" || operator === "NOT IN") && Array.isArray(right)) {
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

// Export types for convenience
export type { AddFilterPopoverState, AvailableColumn, ColumnInfo };
