import { FC } from "react";

import type { TimelineSpan } from "../../components/transcript/timeline";

import { computeBarPosition } from "./swimlaneLayout";
import styles from "./TimelineMinimap.module.css";

export interface TimelineMinimapProps {
  /** Root timeline span (always the full timeline). */
  root: TimelineSpan;
  /** Currently drilled-into node. */
  current: TimelineSpan;
}

/**
 * Minimap row rendered inside the swimlane grid.
 *
 * Uses `display: contents` so it participates in the parent's 3-column grid.
 * A thin track shows the full timeline; two vertical tick markers indicate
 * the start and end of the current zoom region. At root the ticks sit at the
 * track edges and blend in; as you drill deeper they move inward.
 */
export const TimelineMinimap: FC<TimelineMinimapProps> = ({
  root,
  current,
}) => {
  const { left, width } = computeBarPosition(
    current.startTime,
    current.endTime,
    root.startTime,
    root.endTime
  );

  return (
    <div className={styles.row}>
      <div />
      <div className={styles.minimap}>
        <div className={styles.track} />
        <div className={styles.marker} style={{ left: `${left}%` }} />
        <div className={styles.marker} style={{ left: `${left + width}%` }} />
      </div>
      <div />
    </div>
  );
};
