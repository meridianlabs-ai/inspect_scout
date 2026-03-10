import clsx from "clsx";
import { FC, useCallback, useRef, useState } from "react";

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
  /** Scroll progress within the event list (0–1).
   *  Positioned as a fraction of the selection bar.
   *  `null` or `undefined` = no scrubber shown. */
  scrubberProgress?: number | null;
  /** Called when the user clicks or drags on the selection region.
   *  `progress` is 0–1 representing the target scroll position. */
  onScrub?: (progress: number) => void;
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
  scrubberProgress,
  onScrub,
}) => {
  const regionRef = useRef<HTMLDivElement>(null);
  const draggingRef = useRef(false);
  const localProgressRef = useRef<number | null>(null);
  const [dragging, setDragging] = useState(false);
  const [localProgress, setLocalProgress] = useState<number | null>(null);

  const progressFromPointer = useCallback((clientX: number): number => {
    const rect = regionRef.current?.getBoundingClientRect();
    if (!rect || rect.width === 0) return 0;
    return Math.min(1, Math.max(0, (clientX - rect.left) / rect.width));
  }, []);

  const handlePointerDown = useCallback(
    (e: React.PointerEvent) => {
      if (!onScrub) return;
      e.preventDefault();
      draggingRef.current = true;
      const p = progressFromPointer(e.clientX);
      localProgressRef.current = p;
      setDragging(true);
      setLocalProgress(p);
      regionRef.current?.setPointerCapture(e.pointerId);
    },
    [onScrub, progressFromPointer]
  );

  const handlePointerMove = useCallback(
    (e: React.PointerEvent) => {
      if (!draggingRef.current) return;
      const p = progressFromPointer(e.clientX);
      localProgressRef.current = p;
      setLocalProgress(p);
    },
    [progressFromPointer]
  );

  const handlePointerUp = useCallback(
    (e: React.PointerEvent) => {
      if (!draggingRef.current) return;
      draggingRef.current = false;
      setDragging(false);
      const progress = progressFromPointer(e.clientX);
      // Keep localProgress visible so the scrubber doesn't jump —
      // it will be cleared once scrubberProgress catches up (see below).
      localProgressRef.current = progress;
      setLocalProgress(progress);
      onScrub?.(progress);
    },
    [onScrub, progressFromPointer]
  );

  // Lost pointer capture (e.g. window blur) — commit the last known position.
  const handleLostCapture = useCallback(() => {
    if (!draggingRef.current) return;
    draggingRef.current = false;
    setDragging(false);
    const progress = localProgressRef.current;
    if (progress !== null) onScrub?.(progress);
    // Keep localProgress set — cleared by the effect below.
  }, [onScrub]);

  // Once the scroll-driven scrubberProgress updates after a drag release,
  // clear localProgress so the prop takes over seamlessly (no jump).
  // Uses "adjust state during render" pattern to avoid an effect + setState.
  const [prevScrubberProgress, setPrevScrubberProgress] =
    useState(scrubberProgress);
  if (prevScrubberProgress !== scrubberProgress) {
    setPrevScrubberProgress(scrubberProgress);
    if (!dragging && localProgress !== null) {
      setLocalProgress(null);
    }
  }

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

  // During drag (and briefly after release, until scrubberProgress catches up),
  // show the scrubber at the local position; otherwise use the prop.
  const displayProgress =
    localProgress !== null ? localProgress : scrubberProgress;

  const bar = selection
    ? mapping
      ? {
          left: mapping.toPercent(selection.startTime),
          width: Math.max(
            0,
            mapping.toPercent(selection.endTime) -
              mapping.toPercent(selection.startTime)
          ),
        }
      : computeBarPosition(
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
            ref={regionRef}
            className={styles.selectionRegion}
            style={
              bar.left + bar.width / 2 < 50
                ? { left: `${bar.left}%`, minWidth: `${bar.width}%` }
                : {
                    right: `${100 - bar.left - bar.width}%`,
                    minWidth: `${bar.width}%`,
                  }
            }
            onPointerDown={onScrub ? handlePointerDown : undefined}
            onPointerMove={onScrub ? handlePointerMove : undefined}
            onPointerUp={onScrub ? handlePointerUp : undefined}
            onLostPointerCapture={onScrub ? handleLostCapture : undefined}
          >
            <div className={styles.regionFill} />

            {/* Scroll position scrubber — vertical line + caret below track,
                absolutely positioned inside selectionRegion.
                translateX(-50%) in CSS centers on the left %.
                During drag, uses localProgress for smooth visual feedback;
                onScrub (list scroll) is deferred to pointer release. */}
            {displayProgress != null && (
              <div
                className={styles.scrubber}
                style={{
                  left: `${displayProgress * 100}%`,
                }}
              >
                <div className={styles.scrubberLine} />
                <div className={styles.scrubberCaretUp} />
              </div>
            )}

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
