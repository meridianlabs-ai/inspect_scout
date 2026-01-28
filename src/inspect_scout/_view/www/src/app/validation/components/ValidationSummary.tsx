import { FC, useMemo } from "react";

import { ValidationCase } from "../../../types/api-types";

import styles from "./ValidationSummary.module.css";

interface ValidationSummaryProps {
  cases: ValidationCase[];
}

/**
 * Displays summary statistics for a validation set in a compact inline format:
 * N cases | splits: [badge] [badge]
 */
export const ValidationSummary: FC<ValidationSummaryProps> = ({ cases }) => {
  const stats = useMemo(() => {
    // Group cases by split with counts (only named splits)
    const splitCounts = new Map<string, number>();
    for (const c of cases) {
      if (c.split) {
        splitCounts.set(c.split, (splitCounts.get(c.split) ?? 0) + 1);
      }
    }

    // Sort splits alphabetically
    const sortedSplits = Array.from(splitCounts.entries()).sort(([a], [b]) =>
      a.localeCompare(b)
    );

    return {
      totalCount: cases.length,
      splits: sortedSplits,
      hasSplits: splitCounts.size > 0,
    };
  }, [cases]);

  return (
    <div className={styles.container}>
      <span>{stats.totalCount} cases</span>
      {stats.hasSplits && (
        <>
          <span className={styles.separator}>|</span>
          <span>
            Splits:{" "}
            {stats.splits.map(([split, count], i) => (
              <span key={split}>
                {split} ({count}){i < stats.splits.length - 1 && ", "}
              </span>
            ))}
          </span>
        </>
      )}
    </div>
  );
};
