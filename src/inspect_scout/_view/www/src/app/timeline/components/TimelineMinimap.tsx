import clsx from "clsx";
import { FC, useCallback } from "react";

import type { TimelineSpan } from "../../../components/transcript/timeline";
import { useProperty } from "../../../state/hooks/useProperty";
import { formatDuration, formatDurationShort } from "../../../utils/format";
import { computeBarPosition, formatTokenCount } from "../utils/swimlaneLayout";

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

  // Compute both labels so the container can size to the wider one
  const timeRightLabel = formatDuration(root.startTime, root.endTime);
  const tokenRightLabel = formatTokenCount(root.totalTokens);
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
      {/* Mode label — click to toggle time/tokens.
          Both values are rendered so the cell sizes to the wider one. */}
      <div
        className={clsx(styles.stableLabel, styles.alignRight)}
        onClick={toggle}
      >
        <span className={isTokenMode ? styles.hidden : undefined}>time</span>
        <span className={isTokenMode ? undefined : styles.hidden}>tokens</span>
      </div>

      {/* Bar area */}
      <div className={styles.minimap}>
        <div className={styles.track} />

        {/* Selection region: markers + fill + label.
            A wrapper with min-width ensures visibility even when the
            percentage width is sub-pixel (e.g. 1 min in a 10 hr timeline). */}
        {showRegion && (
          <div
            className={styles.selectionRegion}
            style={{
              left: `${bar.left + bar.width / 2}%`,
              width: `${bar.width}%`,
            }}
          >
            <div className={styles.regionFill} />
            <div className={clsx(styles.marker, styles.markerLeft)} />
            <div className={clsx(styles.marker, styles.markerRight)} />
            <div className={styles.sectionTime}>
              <span className={styles.sectionTimePill} onClick={toggle}>
                {sectionLabel}
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Right edge label — both values rendered for stable width */}
      <div
        className={clsx(styles.stableLabel, styles.alignLeft)}
        onClick={toggle}
      >
        <span className={isTokenMode ? styles.hidden : undefined}>
          {timeRightLabel}
        </span>
        <span className={isTokenMode ? undefined : styles.hidden}>
          {tokenRightLabel}
        </span>
      </div>
    </div>
  );
};
