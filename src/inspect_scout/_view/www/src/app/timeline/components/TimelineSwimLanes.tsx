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
  onMarkerNavigate?: (eventId: string, selectedKey?: string) => void;
  /** Headroom auto-collapse: true when scrolling down while sticky. */
  headroomCollapsed?: boolean;
  /** Called before a layout shift (toggle) so the headroom hook can reset
   *  its anchor and ignore the resulting scroll-position change. */
  onLayoutShift?: () => void;
  /** Map from row key → number of compaction regions (only for rows with compactions). */
  regionCounts?: ReadonlyMap<string, number>;
  /** Default collapsed state when user has no stored preference.
   *  Falls back to `isFlat` (layouts.length <= 1) when undefined. */
  defaultCollapsed?: boolean;
}

// =============================================================================
// Marker glyphs
// =============================================================================

const MARKER_ICONS: Record<string, { icon: string; tooltip: string }> = {
  error: { icon: ApplicationIcons.error, tooltip: "Error event" },
  compaction: {
    icon: ApplicationIcons.compaction,
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
  onLayoutShift,
  regionCounts,
  defaultCollapsed: defaultCollapsedProp,
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

  // When the user explicitly toggles while headroom is collapsed, suppress
  // the headroom override until the scroll direction changes. Without this,
  // `headroomCollapsed` always wins via the `||` below and the toggle has
  // no visible effect.
  //
  // Uses the "adjust state during render" pattern to clear the override
  // when headroomCollapsed changes (avoiding effects + cascading renders).
  const [headroomOverride, setHeadroomOverride] = useState(false);
  const [prevHeadroomCollapsed, setPrevHeadroomCollapsed] =
    useState(headroomCollapsed);
  if (prevHeadroomCollapsed !== headroomCollapsed) {
    setPrevHeadroomCollapsed(headroomCollapsed);
    setHeadroomOverride(false);
  }

  // User preference OR headroom auto-collapse (overlay).
  // Headroom collapses on scroll-down; user preference takes over on scroll-up.
  const effectiveHeadroom = headroomCollapsed && !headroomOverride;
  const isCollapsed =
    (collapsed ?? defaultCollapsedProp ?? isFlat) || effectiveHeadroom;
  const toggleCollapsed = useCallback(() => {
    onLayoutShift?.();
    setHeadroomOverride(true);
    setCollapsed(!isCollapsed);
  }, [isCollapsed, setCollapsed, onLayoutShift]);

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
    const selectedRegionIndex = isRowSelected
      ? (parsedSelection?.regionIndex ?? null)
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
        selectedRegionIndex={selectedRegionIndex}
        regionCount={regionCounts?.get(layout.key)}
        isExpanded={isRowExpanded}
        onToggleExpand={
          hasChildren ? () => handleToggleRowCollapse(layout.key) : undefined
        }
        onSelectRow={() => onSelect(layout.key)}
        onSelectSpan={(spanIndex) =>
          onSelect(buildSelectionKey(layout.key, spanIndex))
        }
        onSelectRegion={(spanIndex, regionIndex) =>
          onSelect(buildSelectionKey(layout.key, spanIndex, regionIndex))
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
  /** The region index that is sub-selected, or null if no region is selected. */
  selectedRegionIndex: number | null;
  /** Number of compaction regions for this row (undefined = no compaction regions). */
  regionCount?: number;
  /** Whether the row's children are expanded. undefined = no children (leaf). */
  isExpanded?: boolean;
  /** Toggle expand/collapse for this row. Only provided for rows with children. */
  onToggleExpand?: () => void;
  /** Select the whole row (label click). */
  onSelectRow: () => void;
  /** Select a specific span within the row (bar click). */
  onSelectSpan: (spanIndex: number) => void;
  /** Select a specific region within a span. */
  onSelectRegion: (spanIndex: number | undefined, regionIndex: number) => void;
  onBranchHover: (forkedAt: string, element: HTMLElement) => void;
  onBranchLeave: () => void;
  onMarkerNavigate?: (eventId: string, selectedKey?: string) => void;
}

const SwimlaneRow: FC<SwimlaneRowProps> = ({
  layout,
  displayName,
  isRowSelected,
  selectedSpanIndex,
  selectedRegionIndex,
  regionCount,
  isExpanded,
  onToggleExpand,
  onSelectRow,
  onSelectSpan,
  onSelectRegion,
  onBranchHover,
  onBranchLeave,
  onMarkerNavigate,
}) => {
  const hasMultipleSpans = layout.spans.length > 1;
  const hasChildren = isExpanded !== undefined;

  // Collect compaction marker positions for region segmentation.
  // Only applicable for single-span rows with compaction markers.
  const compactionMarkerPositions = useMemo(() => {
    if (!regionCount || regionCount <= 1) return null;
    const positions: number[] = [];
    for (const marker of layout.markers) {
      if (marker.compactionIndex !== undefined) {
        positions.push(marker.left);
      }
    }
    return positions.length > 0 ? positions : null;
  }, [regionCount, layout.markers]);

  const handleChevronClick = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      onToggleExpand?.();
    },
    [onToggleExpand]
  );

  // Wrap onMarkerNavigate to include the row key for compaction markers,
  // so the bar gets selected atomically with the event navigation.
  const handleMarkerNavigate = useMemo(() => {
    if (!onMarkerNavigate) return undefined;
    return (eventId: string) => onMarkerNavigate(eventId, layout.key);
  }, [onMarkerNavigate, layout.key]);

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

            // Use region-segmented rendering when this bar has compaction markers
            // and is the selected span (or only span).
            const useRegions =
              compactionMarkerPositions !== null &&
              (!hasMultipleSpans || selectedSpanIndex === spanIndex);

            if (useRegions) {
              return (
                <RegionBarFill
                  key={spanIndex}
                  span={span}
                  isParent={layout.isParent}
                  isBarSelected={isBarSelected}
                  isBarDimmed={isBarDimmed}
                  selectedRegionIndex={selectedRegionIndex}
                  compactionPositions={compactionMarkerPositions}
                  onSelectBar={() =>
                    hasMultipleSpans ? onSelectSpan(spanIndex) : onSelectRow()
                  }
                  onSelectRegion={(regionIndex) =>
                    onSelectRegion(
                      hasMultipleSpans ? spanIndex : undefined,
                      regionIndex
                    )
                  }
                  onDoubleClick={onToggleExpand}
                />
              );
            }

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
              onMarkerNavigate={handleMarkerNavigate}
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
// RegionBarFill (internal) — segmented bar for compaction regions
// =============================================================================

interface RegionBarFillProps {
  span: PositionedSpan;
  isParent: boolean;
  /** Whether the whole bar is selected (row or span level). */
  isBarSelected: boolean;
  /** Whether the bar is dimmed (a sibling span is focused). */
  isBarDimmed: boolean;
  /** Currently selected region index, or null if no region is selected. */
  selectedRegionIndex: number | null;
  /** Left positions (%) of compaction markers within the bar area. */
  compactionPositions: number[];
  /** Select the whole bar (no region). */
  onSelectBar: () => void;
  /** Select a specific region within the bar. */
  onSelectRegion: (regionIndex: number) => void;
  onDoubleClick?: () => void;
}

/**
 * Renders a bar fill split into clickable region segments at compaction marker
 * positions. Each segment spans from one compaction marker to the next (or
 * bar start/end). When no region is selected, all segments look like one
 * continuous bar. When a region is selected, the selected segment is
 * highlighted and others are dimmed.
 */
const RegionBarFill: FC<RegionBarFillProps> = ({
  span,
  isParent,
  isBarSelected,
  isBarDimmed,
  selectedRegionIndex,
  compactionPositions,
  onSelectBar,
  onSelectRegion,
  onDoubleClick,
}) => {
  const barLeft = span.bar.left;
  const barRight = span.bar.left + span.bar.width;

  // Build region boundaries: [barLeft, marker1, marker2, ..., barRight]
  const boundaries = [barLeft, ...compactionPositions, barRight];
  const regionCount = boundaries.length - 1;

  // Track hover via React state so we can coordinate highlighting across segments.
  // When no region is selected, hovering any segment highlights all of them.
  // When a region is selected, only the hovered segment highlights.
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);

  // Suppress hover highlighting immediately after a click so that the segment
  // under the cursor doesn't instantly highlight when selection state changes.
  // Cleared on the next mouseLeave, so fresh mouseEnter events work normally.
  const suppressHoverRef = useRef(false);

  const handleDoubleClick = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      onDoubleClick?.();
    },
    [onDoubleClick]
  );

  // If the bar is dimmed (sibling span focused), render a single dimmed bar
  if (isBarDimmed) {
    return (
      <div
        className={clsx(
          styles.fill,
          isParent && styles.fillParent,
          styles.fillDimmed
        )}
        style={{
          left: `${barLeft}%`,
          width: `${span.bar.width}%`,
        }}
        title={span.description ?? undefined}
        onClick={(e) => {
          e.stopPropagation();
          onSelectBar();
        }}
      />
    );
  }

  const hasRegionSelection = isBarSelected && selectedRegionIndex !== null;

  return (
    <>
      {boundaries.map((start, i) => {
        if (i >= regionCount) return null;
        const end = boundaries[i + 1];
        if (end === undefined || end <= start) return null;

        const segmentLeft = start;
        const segmentWidth = end - start;

        const isSegmentSelected =
          hasRegionSelection && selectedRegionIndex === i;

        // Visual state for each segment depends on three levels:
        // 1. Bar not selected → base opacity; hover highlights all segments
        // 2. Bar selected, no region → selected opacity; hover dims non-hovered segments
        // 3. Region selected → selected segment bright, others dimmed; hover per-segment

        const isFirst = i === 0;
        const isLast = i === regionCount - 1;

        // Determine the opacity class. Exactly one should apply:
        let opacityClass: string | undefined;
        if (hasRegionSelection) {
          // State 3: a specific region is selected
          if (isSegmentSelected) {
            opacityClass = styles.fillSelected;
          } else if (hoveredIndex === i) {
            opacityClass = styles.regionHover;
          } else {
            opacityClass = styles.fillDimmed;
          }
        } else if (isBarSelected) {
          // State 2: bar selected, no region — hover previews region boundaries
          if (hoveredIndex !== null && hoveredIndex !== i) {
            // Non-hovered segments dim to show which region would be selected
            opacityClass = isParent ? styles.fillParent : styles.regionDefault;
          } else {
            opacityClass = styles.fillSelected;
          }
        } else {
          // State 1: bar not selected
          if (hoveredIndex !== null) {
            opacityClass = styles.regionHover;
          } else {
            opacityClass = isParent ? styles.fillParent : styles.regionDefault;
          }
        }

        return (
          <div
            key={i}
            className={clsx(
              styles.regionSegment,
              opacityClass,
              isFirst && styles.regionFirst,
              isLast && styles.regionLast,
              !isFirst && !isLast && styles.regionMiddle
            )}
            style={{
              left: `${segmentLeft}%`,
              width: `${segmentWidth}%`,
            }}
            title={span.description ?? undefined}
            onMouseEnter={() => {
              if (!suppressHoverRef.current) setHoveredIndex(i);
            }}
            onMouseLeave={() => {
              suppressHoverRef.current = false;
              setHoveredIndex(null);
            }}
            onClick={(e) => {
              e.stopPropagation();
              // Suppress hover so the segment under the cursor doesn't
              // instantly highlight after selection state changes.
              suppressHoverRef.current = true;
              setHoveredIndex(null);
              if (isBarSelected && selectedRegionIndex === null) {
                // Bar is already selected at whole level — drill into region
                onSelectRegion(i);
              } else if (hasRegionSelection && selectedRegionIndex === i) {
                // Clicking the already-selected region — back to whole bar
                onSelectBar();
              } else if (hasRegionSelection) {
                // A different region is selected — switch to this one
                onSelectRegion(i);
              } else {
                // Not selected at all — select the whole bar first
                onSelectBar();
              }
            }}
            onDoubleClick={onDoubleClick ? handleDoubleClick : undefined}
          />
        );
      })}
    </>
  );
};

// =============================================================================
// MarkerGlyph (internal)
// =============================================================================

interface MarkerGlyphProps {
  marker: PositionedMarker;
  onBranchHover: (forkedAt: string, element: HTMLElement) => void;
  onBranchLeave: () => void;
  onMarkerNavigate?: (eventId: string, selectedKey?: string) => void;
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
