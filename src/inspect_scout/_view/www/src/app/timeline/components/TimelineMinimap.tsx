import clsx from "clsx";
import { FC, useCallback } from "react";

import type { TimelineSpan } from "../../../components/transcript/timeline";
import { useProperty } from "../../../state/hooks/useProperty";
import {
  formatDuration,
  formatDurationShort,
  formatTime,
} from "../../../utils/format";
import { computeBarPosition, formatTokenCount } from "../utils/swimlaneLayout";
import { computeActiveTime, type TimeMapping } from "../utils/timeMapping";

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
  /** Time mapping for the root node (compresses gaps if present). */
  mapping?: TimeMapping;
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
  mapping,
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

  // When compression is active, show active time (wall-clock minus idle)
  // instead of raw wall-clock duration.
  const hasCompression = mapping?.hasCompression ?? false;

  // Compute both labels so the container can size to the wider one
  const timeRightLabel =
    hasCompression && mapping
      ? formatTime(
          computeActiveTime(
            mapping,
            root.startTime.getTime(),
            root.endTime.getTime()
          )
        )
      : formatDuration(root.startTime, root.endTime);
  const tokenRightLabel = formatTokenCount(root.totalTokens);

  const computeSectionLabel = (): string => {
    if (!selection) return "";
    if (isTokenMode) return formatTokenCount(selection.totalTokens);
    if (hasCompression && mapping) {
      return formatTime(
        computeActiveTime(
          mapping,
          selection.startTime.getTime(),
          selection.endTime.getTime()
        )
      );
    }
    return useShortFormat
      ? formatDurationShort(selection.startTime, selection.endTime)
      : formatDuration(selection.startTime, selection.endTime);
  };
  const sectionLabel = computeSectionLabel();

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

        {/* Selection region: anchored at bar start or end depending on
            which half of the timeline the bar sits in, so text expands
            toward the center and never clips at the near edge. */}
        {showRegion && (
          <div
            className={styles.selectionRegion}
            style={
              bar.left + bar.width / 2 < 50
                ? { left: `${bar.left}%`, minWidth: `${bar.width}%` }
                : { right: `${100 - bar.left - bar.width}%`, minWidth: `${bar.width}%` }
            }
          >
            <div className={styles.regionFill} />
            <div className={styles.marker} />
            <div className={styles.sectionTime}>
              <span className={styles.sectionTimePill} onClick={toggle}>
                {sectionLabel}
              </span>
            </div>
            <div className={styles.marker} />
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
