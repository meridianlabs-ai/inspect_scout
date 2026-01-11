import { clsx } from "clsx";
import { FC, useCallback, useRef, useState } from "react";

import { ApplicationIcons } from "../../components/icons";
import { PopOver } from "../../components/PopOver";
import { ToolDropdownButton } from "../../components/ToolDropdownButton";
import type { SimpleCondition } from "../../query/types";
import { useStore } from "../../state/store";
import { Chip } from "../components/Chip";
import { ChipGroup } from "../components/ChipGroup";

import { ColumnFilterEditor } from "./columnFilter/ColumnFilterEditor";
import { useColumnFilterPopover } from "./columnFilter/useColumnFilterPopover";
import styles from "./TranscriptFilterBar.module.css";

const kCopyCodeDescriptors = [
  { label: "Python", value: "python" },
  { label: "Filter", value: "filter" },
];

export const TranscriptFilterBar: FC<{
  filterCodeValues?: Record<string, string>;
}> = ({ filterCodeValues }) => {
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

  // Filter editing state
  const [editingColumnId, setEditingColumnId] = useState<string | null>(null);
  const chipRefs = useRef<Record<string, HTMLDivElement | null>>({});

  const editingFilter = editingColumnId ? filters[editingColumnId] : null;

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
    rawValue,
    setRawValue,
    operatorOptions,
    isValueDisabled,
    valueSelectRef,
    valueInputRef,
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
    },
    [setIsEditorOpen]
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
        {filterEntries.length > 0 ? (
          filterEntries.map((filter) => {
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
                value={`${filter.condition.operator} ${String(filter.condition.right)}`}
                title={`Edit ${filter.columnId} filter`}
                className={clsx(styles.filterChip, "text-size-smallestest")}
                onClose={() => {
                  removeFilter(filter.columnId);
                }}
                onClick={editFilter(filter.columnId)}
              />
            );
          })
        ) : (
          <div className={clsx("text-size-smallest", styles.filterNone)}>
            None
          </div>
        )}
      </ChipGroup>
      {editingColumnId && editingFilter && (
        <PopOver
          id={`transcript-filter-editor-${editingColumnId}`}
          isOpen={isEditorOpen}
          setIsOpen={setIsEditorOpen}
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
            isValueDisabled={isValueDisabled}
            valueSelectRef={valueSelectRef}
            valueInputRef={valueInputRef}
            onOperatorChange={setOperator}
            onValueChange={setRawValue}
            onCommit={commitAndClose}
            onCancel={cancelAndClose}
          />
        </PopOver>
      )}
      <div className={clsx(styles.actionButtons)}>
        <CopyQueryButton itemValues={filterCodeValues} />
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

  // TODO: Actually copy the text
  return (
    <ToolDropdownButton
      key="query-copy"
      label="Copy"
      icon={icon}
      className={styles.actionButton}
      disabled={Object.keys(itemValues || []).length === 0}
      dropdownAlign="right"
      items={items}
    />
  );
};
