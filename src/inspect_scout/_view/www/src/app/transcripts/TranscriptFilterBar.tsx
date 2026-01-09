import { clsx } from "clsx";
import { FC, useCallback, useState } from "react";

import { ApplicationIcons } from "../../components/icons";
import { ToolDropdownButton } from "../../components/ToolDropdownButton";
import { Condition } from "../../query";
import { useStore } from "../../state/store";
import { Chip } from "../components/Chip";
import { ChipGroup } from "../components/ChipGroup";

import styles from "./TranscriptFilterBar.module.css";

export const TranscriptFilterBar: FC = () => {
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
        <CopyQueryButton
          filters={Object.values(filters)
            .map((f) => {
              return f.condition;
            })
            .filter((c) => c !== null)}
        />
      </div>
    </div>
  );
};

const CopyQueryButton: FC<{ filters: Condition[] }> = ({ filters }) => {
  const [icon, setIcon] = useState<string>(ApplicationIcons.copy);

  // TODO: Actually copy the text
  return (
    <ToolDropdownButton
      key="query-copy"
      label="Copy"
      icon={icon}
      className={styles.actionButton}
      disabled={filters.length === 0}
      items={{
        SQL: () => {
          // void navigator.clipboard.writeText();
          setIcon(ApplicationIcons.confirm);
          setTimeout(() => {
            setIcon(ApplicationIcons.copy);
          }, 1250);
        },
        Python: () => {
          //void navigator.clipboard.writeText();
          setIcon(ApplicationIcons.confirm);
          setTimeout(() => {
            setIcon(ApplicationIcons.copy);
          }, 1250);
        },
      }}
    />
  );
};
