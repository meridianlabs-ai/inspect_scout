import { clsx } from "clsx";
import { FC, useCallback } from "react";

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
    </div>
  );
};
