import { FC, useMemo } from "react";

import { ValidationCase } from "../../../types/api-types";
import { getFilenameFromUri } from "../utils";

import styles from "./ValidationSummary.module.css";

interface ValidationSummaryProps {
  uri: string;
  cases: ValidationCase[];
}

/**
 * Displays summary statistics for a validation set:
 * - Filename
 * - Total case count
 * - Splits present
 * - Cases per split
 */
export const ValidationSummary: FC<ValidationSummaryProps> = ({
  uri,
  cases,
}) => {
  const stats = useMemo(() => {
    // Group cases by split
    const splitCounts = new Map<string, number>();
    for (const c of cases) {
      const split = c.split ?? "(no split)";
      splitCounts.set(split, (splitCounts.get(split) ?? 0) + 1);
    }

    // Sort splits alphabetically, but put "(no split)" last
    const sortedSplits = Array.from(splitCounts.entries()).sort(([a], [b]) => {
      if (a === "(no split)") return 1;
      if (b === "(no split)") return -1;
      return a.localeCompare(b);
    });

    return {
      totalCount: cases.length,
      splitCount: splitCounts.size,
      splits: sortedSplits,
    };
  }, [cases]);

  // Extract filename from URI
  const filename = getFilenameFromUri(uri);

  return (
    <div className={styles.container}>
      <div className={styles.filename}>{filename}</div>
      <div className={styles.statsRow}>
        <span className={styles.stat}>
          <span className={styles.statValue}>{stats.totalCount}</span>
          <span className={styles.statLabel}>cases</span>
        </span>
        <span className={styles.separator}>|</span>
        <span className={styles.stat}>
          <span className={styles.statValue}>{stats.splitCount}</span>
          <span className={styles.statLabel}>
            {stats.splitCount === 1 ? "split" : "splits"}
          </span>
        </span>
      </div>
      {stats.splits.length > 0 && (
        <div className={styles.splitsDetail}>
          {stats.splits.map(([split, count]) => (
            <span key={split} className={styles.splitBadge}>
              {split}: {count}
            </span>
          ))}
        </div>
      )}
    </div>
  );
};
