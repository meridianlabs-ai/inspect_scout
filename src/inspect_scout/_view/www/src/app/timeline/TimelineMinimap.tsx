import { FC, useCallback } from "react";

import type { TimelineSpan } from "../../components/transcript/timeline";
import { useProperty } from "../../state/hooks/useProperty";
import { formatDuration } from "../../utils/format";

import { computeBarPosition, formatTokenCount } from "./swimlaneLayout";
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
 * The label and token grid columns are left empty so the minimap's bar area
 * aligns exactly with the swimlane rows. Time labels are positioned inside
 * the bar area at the edges.
 */
export const TimelineMinimap: FC<TimelineMinimapProps> = ({
  root,
  current,
}) => {
  const [showTokens, setShowTokens] = useProperty<boolean>(
    "timeline",
    "minimapShowTokens",
    { defaultValue: false, cleanup: false }
  );
  const isTokenMode = !!showTokens;
  const toggle = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      setShowTokens(!isTokenMode);
    },
    [isTokenMode, setShowTokens]
  );

  const { left, width } = computeBarPosition(
    current.startTime,
    current.endTime,
    root.startTime,
    root.endTime
  );

  const atRoot = current === root;
  const showSectionLabel = !atRoot && width > 15;

  // Labels depend on toggle mode
  const rightLabel = isTokenMode
    ? formatTokenCount(root.totalTokens)
    : formatDuration(root.startTime, root.endTime);
  const sectionLabel = isTokenMode
    ? formatTokenCount(current.totalTokens)
    : formatDuration(current.startTime, current.endTime);

  return (
    <div className={styles.row}>
      {/* Mode label in the label column — right-aligned to sit next to "0" pill */}
      <div className={styles.modeLabel} onClick={toggle}>
        {isTokenMode ? "tokens" : "time"}
      </div>

      {/* Bar area column — all minimap content lives here */}
      <div className={styles.minimap}>
        {/* Edge labels — click to toggle time/tokens */}
        <span className={styles.timeLabelLeft} onClick={toggle}>
          0
        </span>
        <span className={styles.timeLabelRight} onClick={toggle}>
          {rightLabel}
        </span>

        <div className={styles.track} />

        {/* Zoom region fill between markers */}
        {!atRoot && (
          <div
            className={styles.regionFill}
            style={{ left: `${left}%`, width: `${width}%` }}
          />
        )}

        {/* Vertical tick markers at zoom boundaries */}
        {!atRoot && (
          <>
            <div className={styles.marker} style={{ left: `${left}%` }} />
            <div
              className={styles.marker}
              style={{ left: `${left + width}%` }}
            />
          </>
        )}

        {/* Section label pill between markers */}
        {showSectionLabel && (
          <div
            className={styles.sectionTime}
            style={{ left: `${left}%`, width: `${width}%` }}
          >
            <span className={styles.sectionTimePill} onClick={toggle}>
              {sectionLabel}
            </span>
          </div>
        )}
      </div>

      {/* Empty token column — keeps grid alignment with swimlane rows */}
      <div />
    </div>
  );
};
