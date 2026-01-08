import { clsx } from "clsx";
import { FC, useCallback } from "react";

import { useStore } from "../../state/store";
import { Chip } from "../components/Chip";
import { ChipGroup } from "../components/ChipGroup";

import styles from "./TranscriptFilterBar.module.css";

export const TranscriptFilterBar: FC = () => {
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

  return (
    <ChipGroup className={styles.filterBar}>
      {Object.values(filters).map((c, index) => {
        return (
          c && (
            <Chip
              label={c.left}
              value={`${c.operator} ${String(c.right)}`}
              className={clsx(styles.filterChip, "text-size-smallest")}
              onClose={() => {
                const key = Object.keys(filters)[index];
                if (!key) {
                  return;
                }
                removeFilter(key);
              }}
            />
          )
        );
      })}
    </ChipGroup>
  );
};
