import clsx from "clsx";
import { FC, useCallback, useMemo, useState } from "react";

import { ApplicationIcons } from "../../../components/icons";
import { PopOver } from "../../../components/PopOver";
import type { TimelineBranch } from "../../../components/transcript/timeline";
import { useProperty } from "../../../state/hooks/useProperty";
import { formatTime } from "../../../utils/format";
import {
  type TimelineState,
  createBranchSpan,
  findBranchesByForkedAt,
} from "../hooks/useTimeline";
import type {
  PositionedMarker,
  PositionedSpan,
  RowLayout,
} from "../utils/swimlaneLayout";
import { formatTokenCount } from "../utils/swimlaneLayout";

import { TimelineMinimap, type TimelineMinimapProps } from "./TimelineMinimap";
import styles from "./TimelineSwimLanes.module.css";

// =============================================================================
// Types
// =============================================================================

/** Navigation subset of TimelineState needed by the swimlane component. */
export type TimelineNavigation = Pick<
  TimelineState,
  "node" | "selected" | "select" | "clearSelection"
>;

/** Header configuration: root label + optional minimap. */
export interface TimelineHeaderProps {
  rootLabel: string;
  /** Called on header click to scroll the view to the top. */
  onScrollToTop?: () => void;
  /** Minimap props for the zoom indicator. */
  minimap?: TimelineMinimapProps;
}

interface TimelineSwimLanesProps {
  /** Row layouts computed by computeRowLayouts. */
  layouts: RowLayout[];
  /** Timeline navigation state (selection). */
  timeline: TimelineNavigation;
  /** Header configuration. */
  header?: TimelineHeaderProps;
  /** Whether the swimlane is currently in sticky mode (opaque background). */
  isSticky?: boolean;
  /** Force collapsed visual state (e.g. when sticky). */
  forceCollapsed?: boolean;
  /** Disable collapse/expand animation (e.g. during sticky transitions). */
  noAnimation?: boolean;
  /** Called when an error or compaction marker is clicked. */
  onMarkerNavigate?: (eventId: string) => void;
}

// =============================================================================
// Marker glyphs
// =============================================================================

const MARKER_ICONS: Record<string, { icon: string; tooltip: string }> = {
  error: { icon: ApplicationIcons.error, tooltip: "Error event" },
  compaction: {
    icon: ApplicationIcons.compactionMarker,
    tooltip: "Context compaction",
  },
  branch: { icon: ApplicationIcons.fork, tooltip: "View branches" },
};

// =============================================================================
// TimelineSwimLanes
// =============================================================================

export const TimelineSwimLanes: FC<TimelineSwimLanesProps> = ({
  layouts,
  timeline,
  header,
  isSticky,
  forceCollapsed,
  noAnimation,
  onMarkerNavigate,
}) => {
  const { node, selected, select: onSelect, clearSelection } = timeline;

  // Collapse state — persisted across sessions.
  // Auto-collapse when the transcript is flat (single row, no children).
  // Omit defaultValue so we can distinguish "never set" (undefined) from
  // an explicit user choice.
  const [collapsed, setCollapsed] = useProperty<boolean>(
    "timeline",
    "swimlanesCollapsed",
    { cleanup: false }
  );
  const isFlat = layouts.length <= 1;
  // When forceCollapsed (sticky mode), default to collapsed unless
  // the user has explicitly expanded via the toggle (collapsed === false).
  const isCollapsed = forceCollapsed
    ? collapsed !== false
    : (collapsed ?? isFlat);
  const toggleCollapsed = useCallback(() => {
    setCollapsed(!isCollapsed);
  }, [isCollapsed, setCollapsed]);

  // Branch popover state
  const [branchPopover, setBranchPopover] = useState<{
    forkedAt: string;
    element: HTMLElement;
  } | null>(null);

  const handleBranchHover = useCallback(
    (forkedAt: string, element: HTMLElement) => {
      setBranchPopover({ forkedAt, element });
    },
    []
  );

  const handleBranchLeave = useCallback(() => {
    setBranchPopover(null);
  }, []);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLDivElement>) => {
      const rowKeys = layouts.map((l) => l.key);
      const currentIndex = selected ? rowKeys.indexOf(selected) : -1;

      switch (e.key) {
        case "ArrowDown": {
          e.preventDefault();
          const next =
            currentIndex < rowKeys.length - 1 ? currentIndex + 1 : currentIndex;
          const key = rowKeys[next];
          if (key !== undefined) onSelect(key);
          break;
        }
        case "ArrowUp": {
          e.preventDefault();
          const prev = currentIndex > 0 ? currentIndex - 1 : 0;
          const key = rowKeys[prev];
          if (key !== undefined) onSelect(key);
          break;
        }
        case "Escape": {
          e.preventDefault();
          if (branchPopover) {
            setBranchPopover(null);
          } else {
            clearSelection();
          }
          break;
        }
      }
    },
    [layouts, selected, onSelect, clearSelection, branchPopover]
  );

  // Find branches matching the popover's forkedAt UUID.
  const branchLookup = useMemo(() => {
    if (!branchPopover) return null;
    return findBranchesByForkedAt(node, branchPopover.forkedAt);
  }, [branchPopover, node]);

  const parentRow = layouts[0];
  const childRows = layouts.slice(1);

  const renderRow = (layout: RowLayout, displayName?: string) => (
    <SwimlaneRow
      key={layout.key}
      layout={layout}
      displayName={displayName}
      isSelected={selected === layout.key}
      onSelect={() => onSelect(layout.key)}
      onBranchHover={handleBranchHover}
      onBranchLeave={handleBranchLeave}
      onMarkerNavigate={onMarkerNavigate}
    />
  );

  return (
    <div
      className={clsx(styles.swimlane, isSticky && styles.swimlaneSticky)}
      tabIndex={0}
      onKeyDown={handleKeyDown}
      role="grid"
      aria-label="Timeline swimlane"
    >
      {/* Pinned: header row (with minimap) + parent row — always visible */}
      <div className={styles.pinnedSection}>
        {header && <HeaderRow {...header} />}
        {parentRow &&
          renderRow(
            parentRow,
            parentRow.name === "solvers" ? "main" : undefined
          )}
      </div>

      {/* Collapsible child rows */}
      <div
        className={clsx(
          styles.collapsibleSection,
          isCollapsed && styles.collapsibleCollapsed,
          noAnimation && styles.noAnimation
        )}
      >
        <div className={styles.collapsibleInner}>
          {childRows.length > 0 && (
            <div className={styles.scrollSection}>
              {childRows.map((layout) => renderRow(layout))}
            </div>
          )}
        </div>
      </div>

      {/* Collapse toggle on bottom border */}
      <button
        className={styles.collapseToggle}
        onClick={toggleCollapsed}
        title={isCollapsed ? "Expand swimlanes" : "Collapse swimlanes"}
      >
        <i
          className={
            isCollapsed
              ? ApplicationIcons.expand.down
              : ApplicationIcons.collapse.up
          }
        />
      </button>

      <BranchPopover
        isOpen={branchPopover !== null && branchLookup !== null}
        anchor={branchPopover?.element ?? null}
        branches={branchLookup?.branches ?? []}
        onClose={() => setBranchPopover(null)}
      />
    </div>
  );
};

// =============================================================================
// SwimlaneRow (internal)
// =============================================================================

interface SwimlaneRowProps {
  layout: RowLayout;
  /** Override the displayed label (defaults to layout.name). */
  displayName?: string;
  isSelected: boolean;
  onSelect: () => void;
  onBranchHover: (forkedAt: string, element: HTMLElement) => void;
  onBranchLeave: () => void;
  onMarkerNavigate?: (eventId: string) => void;
}

const SwimlaneRow: FC<SwimlaneRowProps> = ({
  layout,
  displayName,
  isSelected,
  onSelect,
  onBranchHover,
  onBranchLeave,
  onMarkerNavigate,
}) => {
  return (
    <div className={styles.row} role="row">
      {/* Label cell — depth-based indentation */}
      <div
        className={clsx(styles.label, isSelected && styles.labelSelected)}
        style={{ paddingLeft: `${0.95 + layout.depth * 0.5}rem` }}
      >
        {displayName ?? layout.name}
      </div>

      {/* Bar area cell */}
      <div className={styles.barArea}>
        <div className={styles.barInner}>
          {/* Fills */}
          {layout.spans.map((span, spanIndex) => (
            <BarFill
              key={spanIndex}
              span={span}
              isParent={layout.isParent}
              isSelected={isSelected}
              onSelect={onSelect}
            />
          ))}

          {/* Markers */}
          {layout.markers.map((marker, i) => (
            <MarkerGlyph
              key={i}
              marker={marker}
              onBranchHover={onBranchHover}
              onBranchLeave={onBranchLeave}
              onMarkerNavigate={onMarkerNavigate}
            />
          ))}
        </div>
      </div>

      {/* Token cell */}
      <div className={styles.tokens}>
        {formatTokenCount(layout.totalTokens)}
      </div>
    </div>
  );
};

// =============================================================================
// HeaderRow (internal)
// =============================================================================

const HeaderRow: FC<TimelineHeaderProps> = ({
  rootLabel,
  minimap,
  onScrollToTop,
}) => {
  return (
    <div className={styles.breadcrumbRow}>
      <button className={styles.breadcrumbCurrent} onClick={onScrollToTop}>
        {rootLabel === "solvers" ? "main" : rootLabel}
      </button>
      {minimap && <TimelineMinimap {...minimap} />}
    </div>
  );
};

// =============================================================================
// BarFill (internal)
// =============================================================================

interface BarFillProps {
  span: PositionedSpan;
  isParent: boolean;
  isSelected: boolean;
  onSelect: () => void;
}

const BarFill: FC<BarFillProps> = ({
  span,
  isParent,
  isSelected,
  onSelect,
}) => {
  const handleClick = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      onSelect();
    },
    [onSelect]
  );

  return (
    <div
      className={clsx(
        styles.fill,
        isParent && styles.fillParent,
        isSelected && styles.fillSelected
      )}
      style={{
        left: `${span.bar.left}%`,
        width: `${span.bar.width}%`,
      }}
      title={span.description ?? undefined}
      onClick={handleClick}
    />
  );
};

// =============================================================================
// MarkerGlyph (internal)
// =============================================================================

interface MarkerGlyphProps {
  marker: PositionedMarker;
  onBranchHover: (forkedAt: string, element: HTMLElement) => void;
  onBranchLeave: () => void;
  onMarkerNavigate?: (eventId: string) => void;
}

const MarkerGlyph: FC<MarkerGlyphProps> = ({
  marker,
  onBranchHover,
  onBranchLeave,
  onMarkerNavigate,
}) => {
  const icon = MARKER_ICONS[marker.kind]?.icon ?? "bi bi-question-circle";
  const kindClass =
    marker.kind === "error"
      ? styles.markerError
      : marker.kind === "compaction"
        ? styles.markerCompaction
        : styles.markerBranch;

  const handleClick = useCallback(
    (e: React.MouseEvent<HTMLSpanElement>) => {
      if (marker.kind === "branch") {
        e.stopPropagation();
        onBranchHover(marker.reference, e.currentTarget);
      } else if (marker.reference && onMarkerNavigate) {
        e.stopPropagation();
        onMarkerNavigate(marker.reference);
      }
    },
    [marker.kind, marker.reference, onMarkerNavigate, onBranchHover]
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLSpanElement>) => {
      if (marker.kind === "branch" && (e.key === "Enter" || e.key === " ")) {
        e.preventDefault();
        e.stopPropagation();
        onBranchHover(marker.reference, e.currentTarget);
      }
    },
    [marker.kind, marker.reference, onBranchHover]
  );

  const handleMouseEnter = useCallback(
    (e: React.MouseEvent<HTMLSpanElement>) => {
      if (marker.kind === "branch") {
        onBranchHover(marker.reference, e.currentTarget);
      }
    },
    [marker.kind, marker.reference, onBranchHover]
  );

  const handleMouseLeave = useCallback(() => {
    if (marker.kind === "branch") {
      onBranchLeave();
    }
  }, [marker.kind, onBranchLeave]);

  // Branch markers show a popover on hover — no tooltip needed
  const isBranch = marker.kind === "branch";

  return (
    <span
      className={clsx(styles.marker, kindClass)}
      style={{ left: `${marker.left}%` }}
      title={isBranch ? undefined : marker.tooltip}
      onClick={handleClick}
      onKeyDown={isBranch ? handleKeyDown : undefined}
      onMouseEnter={isBranch ? handleMouseEnter : undefined}
      onMouseLeave={isBranch ? handleMouseLeave : undefined}
      tabIndex={isBranch ? 0 : undefined}
      role={isBranch ? "button" : undefined}
      aria-haspopup={isBranch ? "true" : undefined}
      aria-label={isBranch ? "Show branches" : undefined}
    >
      {marker.kind !== "error" && <i className={icon} />}
    </span>
  );
};

// =============================================================================
// BranchPopover (internal — informational only)
// =============================================================================

interface BranchPopoverProps {
  isOpen: boolean;
  anchor: HTMLElement | null;
  branches: Array<{ branch: TimelineBranch; index: number }>;
  onClose: () => void;
}

const BranchPopover: FC<BranchPopoverProps> = ({
  isOpen,
  anchor,
  branches,
  onClose,
}) => {
  return (
    <PopOver
      id="branch-popover"
      isOpen={isOpen}
      setIsOpen={(open) => {
        if (!open) onClose();
      }}
      positionEl={anchor}
      placement="bottom"
      showArrow={true}
      hoverDelay={0}
      closeOnMouseLeave={true}
      styles={{ padding: "4px 0" }}
    >
      <div className={styles.branchPopover}>
        {branches.map(({ branch, index }) => {
          const span = createBranchSpan(branch, index);
          const durationSec =
            (branch.endTime.getTime() - branch.startTime.getTime()) / 1000;
          return (
            <div key={`branch-${index}`} className={styles.branchEntry}>
              <span className={styles.branchLabel}>{span.name}</span>
              <span className={styles.branchMeta}>
                {formatTokenCount(branch.totalTokens)}
                {" \u00B7 "}
                {formatTime(durationSec)}
              </span>
            </div>
          );
        })}
      </div>
    </PopOver>
  );
};
