import { FC } from "react";

import { formatDuration } from "../../utils/format";

import styles from "./TimelineBreadcrumb.module.css";
import type { BreadcrumbSegment } from "./useTimeline";

interface TimelineBreadcrumbProps {
  /** Breadcrumb segments from useTimeline. */
  breadcrumbs: BreadcrumbSegment[];
  /** Start time of the current node. */
  startTime: Date;
  /** End time of the current node. */
  endTime: Date;
  /** Whether the user is at root (controls back arrow visibility). */
  atRoot: boolean;
  /** Navigate up one level. */
  onGoUp: () => void;
  /** Navigate to a specific breadcrumb path. */
  onNavigate: (path: string) => void;
}

export const TimelineBreadcrumb: FC<TimelineBreadcrumbProps> = ({
  breadcrumbs,
  startTime,
  endTime,
  atRoot,
  onGoUp,
  onNavigate,
}) => {
  return (
    <div className={styles.breadcrumbRow}>
      <button
        className={styles.backButton}
        onClick={onGoUp}
        disabled={atRoot}
        title="Go up one level (Escape)"
      >
        &larr;
      </button>
      <div className={styles.segments}>
        {breadcrumbs.map((segment, i) => {
          const isLast = i === breadcrumbs.length - 1;
          return (
            <span key={segment.path + i} className={styles.segmentGroup}>
              {i > 0 && <span className={styles.divider}>{"\u203A"}</span>}
              {isLast ? (
                <span className={styles.segmentCurrent}>{segment.label}</span>
              ) : (
                <button
                  className={styles.segmentButton}
                  onClick={() => onNavigate(segment.path)}
                >
                  {segment.label}
                </button>
              )}
            </span>
          );
        })}
      </div>
      <span className={styles.tokenCount}>
        {formatDuration(startTime, endTime)}
      </span>
    </div>
  );
};
