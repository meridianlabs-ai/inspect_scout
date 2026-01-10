import { clsx } from "clsx";
import { FC, useCallback, useState } from "react";

import { ApplicationIcons } from "../../components/icons";
import { ToolDropdownButton } from "../../components/ToolDropdownButton";
import { useStore } from "../../state/store";
import { Chip } from "../components/Chip";
import { ChipGroup } from "../components/ChipGroup";

import styles from "./TranscriptFilterBar.module.css";

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

  // Editing filter
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
                label={filter.columnId}
                value={`${filter.condition.operator} ${String(filter.condition.right)}`}
                title={`Edit ${filter.columnId} filter`}
                className={clsx(styles.filterChip, "text-size-smallestest")}
                onClose={() => {
                  removeFilter(filter.columnId);
                }}
              />
            );
          })
        ) : (
          <div className={clsx("text-size-smallest", styles.filterNone)}>
            None
          </div>
        )}
      </ChipGroup>
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

  const itemDescriptors = [
    { label: "SQL (duckdb)", value: "duckdb" },
    { label: "SQL (postgres)", value: "postgres" },
    { label: "SQL (sqlite)", value: "sqlite" },
    // { label: "Python", value: "python" },
  ];

  const items = itemDescriptors.reduce(
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
