import clsx from "clsx";
import { FC, useCallback, useMemo, useRef, useState } from "react";

import { ApplicationIcons } from "../../../components/icons";
import { PopOver } from "../../../components/PopOver";
import type { TimelineBranch } from "../../../components/transcript/timeline";
import { useProperty } from "../../../state/hooks/useProperty";
import { useStore } from "../../../state/store";
import { formatTime } from "../../../utils/format";
import {
  type TimelineState,
  createBranchSpan,
  findBranchesByForkedAt,
} from "../hooks/useTimeline";
import type { UseTimelineConfigResult } from "../hooks/useTimelineConfig";
import { buildSelectionKey, parseSelection } from "../timelineEventNodes";
import type {
  PositionedMarker,
  PositionedSpan,
  RowLayout,
} from "../utils/swimlaneLayout";
import { formatTokenCount } from "../utils/swimlaneLayout";

import { TimelineMinimap, type TimelineMinimapProps } from "./TimelineMinimap";
import { TimelineOptionsPopover } from "./TimelineOptionsPopover";
import {
  TimelineSelector,
  type TimelineSelectorProps,
} from "./TimelineSelector";
import styles from "./TimelineSwimLanes.module.css";

// =============================================================================
// Breadcrumb computation
// =============================================================================

export interface BreadcrumbSegment {
  /** Display name for this segment. */
  label: string;
  /** Selection key to navigate to this segment. */
  key: string;
}

/**
 * Builds breadcrumb segments from the layouts and selected key.
 *
 * The selected key encodes tree position (e.g. "transcript/build/test").
 * We find ancestor rows by matching prefix keys, producing a trail like:
 * [main, Build, Test] where "Test" is the currently selected row.
 */
export function buildBreadcrumbs(
  layouts: RowLayout[],
  selectedRowKey: string | null
): BreadcrumbSegment[] {
  if (!selectedRowKey) return [];

  // Build a lookup from key to layout
  const byKey = new Map<string, RowLayout>();
  for (const layout of layouts) {
    byKey.set(layout.key, layout);
  }

  // Walk the key segments to find ancestor rows.
  // Key format: "transcript/build/test" → ancestors are "transcript", "transcript/build"
  const parts = selectedRowKey.split("/");
  const segments: BreadcrumbSegment[] = [];

  for (let i = 1; i <= parts.length; i++) {
    const ancestorKey = parts.slice(0, i).join("/");
    const layout = byKey.get(ancestorKey);
    if (layout) {
      const label =
        layout.depth === 0 && layout.name === "solvers" ? "main" : layout.name;
      segments.push({ label, key: layout.key });
    }
  }

  return segments;
}

// =============================================================================
// Types
// =============================================================================

/** Navigation subset of TimelineState needed by the swimlane component. */
export type TimelineNavigation = Pick<
  TimelineState,
  "node" | "selected" | "select" | "clearSelection"
>;

/** Header configuration: root label + optional minimap + breadcrumbs. */
export interface TimelineHeaderProps {
  rootLabel: string;
  /** Called on header click to scroll the view to the top. */
  onScrollToTop?: () => void;
  /** Minimap props for the zoom indicator. */
  minimap?: TimelineMinimapProps;
  /** Breadcrumb segments derived from the selected row's ancestry. */
  breadcrumbs?: BreadcrumbSegment[];
  /** Called when a breadcrumb segment is clicked. */
  onBreadcrumbSelect?: (key: string) => void;
  /** Timeline config for the options popover. When provided, shows the options button. */
  timelineConfig?: UseTimelineConfigResult;
  /** Timeline selector for switching between multiple timelines. */
  timelineSelector?: TimelineSelectorProps;
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
  /** Called when an error or compaction marker is clicked. */
  onMarkerNavigate?: (eventId: string) => void;
  /** Headroom auto-collapse: true when scrolling down while sticky. */
  headroomCollapsed?: boolean;
  /** Called when the user explicitly toggles collapse (locks headroom). */
  onToggle?: () => void;
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
  onMarkerNavigate,
  headroomCollapsed = false,
  onToggle,
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
  // User preference OR headroom auto-collapse (overlay).
  // Headroom collapses on scroll-down; user preference takes over on scroll-up.
  const isCollapsed = (collapsed ?? isFlat) || headroomCollapsed;
  const toggleCollapsed = useCallback(() => {
    onToggle?.();
    setCollapsed(!isCollapsed);
  }, [isCollapsed, setCollapsed, onToggle]);

  // Row expand/collapse state — stored in Zustand collapsedBuckets.
  // Keys that are collapsed have `true` in the bucket; default is expanded.
  const collapsedBucket = useStore(
    (state) => state.collapsedBuckets["timeline-swimlane-rows"]
  );
  const stableCollapsedBucket = useMemo(
    () => collapsedBucket ?? {},
    [collapsedBucket]
  );
  const setRowCollapsed = useStore((state) => state.setCollapsed);

  // Compute which rows have children (need a chevron dongle)
  const parentKeys = useMemo(() => {
    const keys = new Set<string>();
    for (const layout of layouts) {
      // A row is a parent if any other row's key starts with it + "/"
      const prefix = layout.key + "/";
      for (const other of layouts) {
        if (other.key.startsWith(prefix)) {
          keys.add(layout.key);
          break;
        }
      }
    }
    return keys;
  }, [layouts]);

  // Determine if a row is collapsed. Default: depth >= 1 parent rows start
  // collapsed (only first level shown). Explicit store entries override.
  const isRowCollapsed = useCallback(
    (rowKey: string): boolean => {
      const explicit = stableCollapsedBucket[rowKey];
      if (explicit !== undefined) return explicit;
      // Default: collapse parent rows at depth >= 1
      const layout = layouts.find((l) => l.key === rowKey);
      return (
        layout !== undefined && layout.depth >= 1 && parentKeys.has(rowKey)
      );
    },
    [stableCollapsedBucket, layouts, parentKeys]
  );

  // Filter out rows whose ancestors are collapsed
  const visibleLayouts = useMemo(() => {
    return layouts.filter((layout) => {
      // Check if any ancestor is collapsed
      const parts = layout.key.split("/");
      for (let i = 1; i < parts.length; i++) {
        const ancestorKey = parts.slice(0, i).join("/");
        if (isRowCollapsed(ancestorKey)) {
          return false;
        }
      }
      return true;
    });
  }, [layouts, isRowCollapsed]);

  const handleToggleRowCollapse = useCallback(
    (rowKey: string) => {
      const current = isRowCollapsed(rowKey);
      setRowCollapsed("timeline-swimlane-rows", rowKey, !current);
    },
    [isRowCollapsed, setRowCollapsed]
  );

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

  // Parse selection into row key + optional span index
  const parsedSelection = useMemo(() => parseSelection(selected), [selected]);
  const selectedRowKey = parsedSelection?.rowKey ?? null;

  // Compute breadcrumbs from the selected row's ancestry
  const breadcrumbs = useMemo(
    () => buildBreadcrumbs(layouts, selectedRowKey),
    [layouts, selectedRowKey]
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLDivElement>) => {
      const rowKeys = visibleLayouts.map((l) => l.key);
      // Arrow keys navigate by row key (strip span index)
      const currentIndex = selectedRowKey
        ? rowKeys.indexOf(selectedRowKey)
        : -1;

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
    [visibleLayouts, selectedRowKey, onSelect, clearSelection, branchPopover]
  );

  // Find branches matching the popover's forkedAt UUID.
  const branchLookup = useMemo(() => {
    if (!branchPopover) return null;
    return findBranchesByForkedAt(node, branchPopover.forkedAt);
  }, [branchPopover, node]);

  const parentRow = visibleLayouts[0];
  const childRows = visibleLayouts.slice(1);

  const renderRow = (layout: RowLayout, displayName?: string) => {
    const isRowSelected = selectedRowKey === layout.key;
    const selectedSpanIndex = isRowSelected
      ? (parsedSelection?.spanIndex ?? null)
      : null;
    const hasChildren = parentKeys.has(layout.key);
    const isRowExpanded = hasChildren ? !isRowCollapsed(layout.key) : undefined;

    return (
      <SwimlaneRow
        key={layout.key}
        layout={layout}
        displayName={displayName}
        isRowSelected={isRowSelected}
        selectedSpanIndex={selectedSpanIndex}
        isExpanded={isRowExpanded}
        onToggleExpand={
          hasChildren ? () => handleToggleRowCollapse(layout.key) : undefined
        }
        onSelectRow={() => onSelect(layout.key)}
        onSelectSpan={(spanIndex) =>
          onSelect(buildSelectionKey(layout.key, spanIndex))
        }
        onBranchHover={handleBranchHover}
        onBranchLeave={handleBranchLeave}
        onMarkerNavigate={onMarkerNavigate}
      />
    );
  };

  return (
    <div
      className={clsx(styles.swimlane, isSticky && styles.swimlaneSticky)}
      tabIndex={0}
      onKeyDown={handleKeyDown}
      role="grid"
      aria-label="Timeline swimlane"
    >
      {/* Pinned: header row (breadcrumbs + minimap) — always visible */}
      <div className={styles.pinnedSection}>
        {header && (
          <HeaderRow
            {...header}
            breadcrumbs={breadcrumbs}
            onBreadcrumbSelect={onSelect}
          />
        )}
      </div>

      {/* Collapsible: parent row + child rows */}
      <div
        className={clsx(
          styles.collapsibleSection,
          isCollapsed && styles.collapsibleCollapsed
        )}
      >
        <div className={styles.collapsibleInner}>
          {parentRow &&
            renderRow(
              parentRow,
              parentRow.name === "solvers" ? "main" : undefined
            )}
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
  /** Whether this row is selected (whole row or a span within it). */
  isRowSelected: boolean;
  /** The span index that is sub-selected, or null if the whole row is selected. */
  selectedSpanIndex: number | null;
  /** Whether the row's children are expanded. undefined = no children (leaf). */
  isExpanded?: boolean;
  /** Toggle expand/collapse for this row. Only provided for rows with children. */
  onToggleExpand?: () => void;
  /** Select the whole row (label click). */
  onSelectRow: () => void;
  /** Select a specific span within the row (bar click). */
  onSelectSpan: (spanIndex: number) => void;
  onBranchHover: (forkedAt: string, element: HTMLElement) => void;
  onBranchLeave: () => void;
  onMarkerNavigate?: (eventId: string) => void;
}

const SwimlaneRow: FC<SwimlaneRowProps> = ({
  layout,
  displayName,
  isRowSelected,
  selectedSpanIndex,
  isExpanded,
  onToggleExpand,
  onSelectRow,
  onSelectSpan,
  onBranchHover,
  onBranchLeave,
  onMarkerNavigate,
}) => {
  const hasMultipleSpans = layout.spans.length > 1;
  const hasChildren = isExpanded !== undefined;

  const handleChevronClick = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      onToggleExpand?.();
    },
    [onToggleExpand]
  );

  return (
    <div className={styles.row} role="row">
      {/* Label cell — depth-based indentation; clicking selects the whole row */}
      <div
        className={clsx(styles.label, isRowSelected && styles.labelSelected)}
        style={{ paddingLeft: `${0.3 + layout.depth * 0.5}rem` }}
        onClick={onSelectRow}
      >
        {hasChildren ? (
          <span
            className={styles.chevron}
            onClick={handleChevronClick}
            role="button"
            aria-label={isExpanded ? "Collapse" : "Expand"}
          >
            <i
              className={
                isExpanded
                  ? ApplicationIcons.chevron.down
                  : ApplicationIcons.chevron.right
              }
            />
          </span>
        ) : (
          <span className={styles.chevronSpacer} />
        )}
        {displayName ?? layout.name}
      </div>

      {/* Bar area cell */}
      <div className={styles.barArea}>
        <div className={styles.barInner}>
          {/* Fills */}
          {layout.spans.map((span, spanIndex) => {
            // For multi-span rows: a bar is "selected" only if it's the sub-selected span,
            // or if the whole row is selected (no span index).
            // For single-span rows: selected when the row is selected.
            const isBarSelected =
              isRowSelected &&
              (!hasMultipleSpans ||
                selectedSpanIndex === null ||
                selectedSpanIndex === spanIndex);
            // "Dimmed" = row is selected but a different specific span is focused
            const isBarDimmed =
              isRowSelected &&
              hasMultipleSpans &&
              selectedSpanIndex !== null &&
              selectedSpanIndex !== spanIndex;

            return (
              <BarFill
                key={spanIndex}
                span={span}
                isParent={layout.isParent}
                isSelected={isBarSelected}
                isDimmed={isBarDimmed}
                onSelect={() =>
                  hasMultipleSpans ? onSelectSpan(spanIndex) : onSelectRow()
                }
                onDoubleClick={onToggleExpand}
              />
            );
          })}

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
  breadcrumbs,
  onBreadcrumbSelect,
  timelineConfig,
  timelineSelector,
}) => {
  const hasBreadcrumbs = breadcrumbs && breadcrumbs.length > 1;
  const rootDisplay = rootLabel === "solvers" ? "main" : rootLabel;

  const [optionsOpen, setOptionsOpen] = useState(false);
  const optionsButtonRef = useRef<HTMLButtonElement | null>(null);

  return (
    <div className={styles.breadcrumbRow}>
      {timelineSelector && (
        <>
          <TimelineSelector {...timelineSelector} />
          <span className={styles.breadcrumbDivider}>/</span>
        </>
      )}
      {hasBreadcrumbs ? (
        <div className={styles.breadcrumbTrail}>
          {breadcrumbs.map((segment, i) => {
            const isLast = i === breadcrumbs.length - 1;
            return (
              <span key={segment.key} className={styles.breadcrumbSegment}>
                {i > 0 && <span className={styles.breadcrumbDivider}>/</span>}
                {isLast ? (
                  <span className={styles.breadcrumbCurrent}>
                    {segment.label}
                  </span>
                ) : (
                  <button
                    className={styles.breadcrumbLink}
                    onClick={() => onBreadcrumbSelect?.(segment.key)}
                  >
                    {segment.label}
                  </button>
                )}
              </span>
            );
          })}
        </div>
      ) : (
        <button className={styles.breadcrumbCurrent} onClick={onScrollToTop}>
          {rootDisplay}
        </button>
      )}
      {timelineConfig && (
        <button
          ref={optionsButtonRef}
          type="button"
          className={styles.optionsButton}
          onClick={() => setOptionsOpen((prev) => !prev)}
          title="Timeline options"
          aria-label="Timeline options"
        >
          <i className={ApplicationIcons.threeDots} />
        </button>
      )}
      {minimap && <TimelineMinimap {...minimap} />}
      {timelineConfig && (
        <TimelineOptionsPopover
          isOpen={optionsOpen}
          setIsOpen={setOptionsOpen}
          // eslint-disable-next-line react-hooks/refs -- positionEl accepts null; PopOver handles this in effects
          positionEl={optionsButtonRef.current}
          config={timelineConfig}
        />
      )}
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
  /** Row is selected but a different span is focused. */
  isDimmed: boolean;
  onSelect: () => void;
  /** Toggle expand/collapse on double-click. Only for rows with children. */
  onDoubleClick?: () => void;
}

const BarFill: FC<BarFillProps> = ({
  span,
  isParent,
  isSelected,
  isDimmed,
  onSelect,
  onDoubleClick,
}) => {
  const handleClick = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      onSelect();
    },
    [onSelect]
  );

  const handleDoubleClick = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      onDoubleClick?.();
    },
    [onDoubleClick]
  );

  return (
    <div
      className={clsx(
        styles.fill,
        isParent && styles.fillParent,
        isSelected && styles.fillSelected,
        isDimmed && styles.fillDimmed
      )}
      style={{
        left: `${span.bar.left}%`,
        width: `${span.bar.width}%`,
      }}
      title={span.description ?? undefined}
      onClick={handleClick}
      onDoubleClick={onDoubleClick ? handleDoubleClick : undefined}
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
