import { FC, useCallback } from "react";

import type { TimelineSpan } from "../../components/transcript/timeline";
import { useProperty } from "../../state/hooks/useProperty";
import { formatDuration, formatDurationShort } from "../../utils/format";

import { computeBarPosition, formatTokenCount } from "./swimlaneLayout";
import styles from "./TimelineMinimap.module.css";

export interface MinimapSelection {
  startTime: Date;
  endTime: Date;
  totalTokens: number;
}

export interface TimelineMinimapProps {
  /** Root timeline span (always the full timeline). */
  root: TimelineSpan;
  /** Currently selected swimlane row, if any. */
  selection?: MinimapSelection;
}

/**
 * Compact minimap showing the selected row's position within the full timeline.
 *
 * Renders as a self-contained flex row: mode label + bar area.
 * Designed to sit inside the breadcrumb row, right-aligned.
 */
export const TimelineMinimap: FC<TimelineMinimapProps> = ({
  root,
  selection,
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

  const bar = selection
    ? computeBarPosition(
        selection.startTime,
        selection.endTime,
        root.startTime,
        root.endTime
      )
    : null;

  const showRegion = bar !== null;
  const useShortFormat = bar !== null && bar.width <= 15;

  // Labels depend on toggle mode
  const rightLabel = isTokenMode
    ? formatTokenCount(root.totalTokens)
    : formatDuration(root.startTime, root.endTime);
  const sectionLabel =
    selection && isTokenMode
      ? formatTokenCount(selection.totalTokens)
      : selection
        ? useShortFormat
          ? formatDurationShort(selection.startTime, selection.endTime)
          : formatDuration(selection.startTime, selection.endTime)
        : "";

  return (
    <div className={styles.container}>
      {/* Mode label — click to toggle time/tokens */}
      <div className={styles.modeLabel} onClick={toggle}>
        {isTokenMode ? "tokens" : "time"}
      </div>

      {/* Bar area — all minimap content lives here */}
      <div className={styles.minimap}>
        {/* Edge labels — click to toggle time/tokens */}
        <span className={styles.timeLabelLeft} onClick={toggle}>
          0
        </span>
        <span className={styles.timeLabelRight} onClick={toggle}>
          {rightLabel}
        </span>

        <div className={styles.track} />

        {/* Selection region fill between markers */}
        {showRegion && (
          <div
            className={styles.regionFill}
            style={{ left: `${bar.left}%`, width: `${bar.width}%` }}
          />
        )}

        {/* Vertical tick markers at selection boundaries */}
        {showRegion && (
          <>
            <div className={styles.marker} style={{ left: `${bar.left}%` }} />
            <div
              className={styles.marker}
              style={{ left: `${bar.left + bar.width}%` }}
            />
          </>
        )}

        {/* Section label pill between markers */}
        {showRegion && (
          <div
            className={styles.sectionTime}
            style={{ left: `${bar.left}%`, width: `${bar.width}%` }}
          >
            <span className={styles.sectionTimePill} onClick={toggle}>
              {sectionLabel}
            </span>
          </div>
        )}
      </div>
    </div>
  );
};
