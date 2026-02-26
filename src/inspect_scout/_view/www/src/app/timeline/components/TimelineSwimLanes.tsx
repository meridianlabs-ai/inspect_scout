import clsx from "clsx";
import { FC, useCallback, useMemo, useState } from "react";

import { ApplicationIcons } from "../../../components/icons";
import { PopOver } from "../../../components/PopOver";
import type {
  TimelineBranch,
  TimelineSpan,
} from "../../../components/transcript/timeline";
import { useProperty } from "../../../state/hooks/useProperty";
import { formatTime } from "../../../utils/format";
import {
  type BreadcrumbSegment,
  createBranchSpan,
  findBranchesByForkedAt,
  parsePathSegment,
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

interface TimelineSwimLanesProps {
  /** Row layouts computed by computeRowLayouts. */
  layouts: RowLayout[];
  /** Currently selected span identifier (e.g. "explore" or "explore-2"), or null. */
  selected: string | null;
  /** The current drill-down node (for branch lookup). */
  node: TimelineSpan;
  /** Called when a span is clicked (selection). */
  onSelect: (name: string, spanIndex?: number) => void;
  /** Called when a span's drill-down chevron or a branch popover entry is clicked. */
  onDrillDown: (name: string, spanIndex?: number) => void;
  /** Called on Escape key (go up). */
  onGoUp: () => void;
  /** Minimap props for the zoom indicator row. */
  minimap?: TimelineMinimapProps;
  /** Breadcrumb props for the navigation row. */
  breadcrumb?: BreadcrumbRowProps;
  /** Whether the swimlane is currently in sticky mode (opaque background). */
  isSticky?: boolean;
  /** Force collapsed visual state (e.g. when sticky). */
  forceCollapsed?: boolean;
  /** Disable collapse/expand animation (e.g. during sticky transitions). */
  noAnimation?: boolean;
  /** Show error markers on swimlane bars. Defaults to false. */
  showErrorMarkers?: boolean;
  /** Called when an error or compaction marker is clicked. */
  onMarkerNavigate?: (eventId: string) => void;
}

export interface BreadcrumbRowProps {
  breadcrumbs: BreadcrumbSegment[];
  atRoot: boolean;
  onGoUp: () => void;
  onNavigate: (path: string) => void;
  /** Currently selected row name, shown as a read-only tail segment. */
  selected?: string | null;
}

// =============================================================================
// Selection helpers
// =============================================================================

interface ParsedSelection {
  name: string;
  spanIndex: number | null;
}

function parseSelected(selected: string | null): ParsedSelection | null {
  if (!selected) return null;
  return parsePathSegment(selected);
}

/**
 * Check if a specific span within a row is the selected one.
 * For single-span rows, any selection of that row name matches.
 * For multi-span rows, the span index must match.
 */
function isSpanSelected(
  layout: RowLayout,
  spanIndex: number,
  parsed: ParsedSelection | null
): boolean {
  if (!parsed) return false;
  if (layout.name.toLowerCase() !== parsed.name.toLowerCase()) return false;

  if (layout.spans.length === 1) {
    // Single-span row: any selection of this name matches
    return true;
  }

  // Multi-span row: match by span index (1-indexed)
  // No suffix (spanIndex === null) → first span
  const selectedIdx = parsed.spanIndex ?? 1;
  return selectedIdx === spanIndex + 1;
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
  selected,
  node,
  onSelect,
  onDrillDown,
  onGoUp,
  minimap,
  breadcrumb,
  isSticky,
  forceCollapsed,
  noAnimation,
  showErrorMarkers,
  onMarkerNavigate,
}) => {
  const parsedSelection = useMemo(() => parseSelected(selected), [selected]);

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

  const handleBranchSelect = useCallback(
    (branchSegment: string) => {
      // Compute the owner path at select time to avoid stale closure issues
      const lookup = findBranchesByForkedAt(
        node,
        branchPopover?.forkedAt ?? ""
      );
      setBranchPopover(null);
      // Build the full drill-down path: owner path segments + branch segment
      if (lookup && lookup.ownerPath.length > 0) {
        const fullSegment = [...lookup.ownerPath, branchSegment].join("/");
        onDrillDown(fullSegment);
      } else {
        onDrillDown(branchSegment);
      }
    },
    [onDrillDown, node, branchPopover?.forkedAt]
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLDivElement>) => {
      const rowNames = layouts.map((l) => l.name);
      const currentRowName = parsedSelection?.name.toLowerCase() ?? null;
      const currentIndex = currentRowName
        ? rowNames.findIndex((n) => n.toLowerCase() === currentRowName)
        : -1;

      switch (e.key) {
        case "ArrowDown": {
          e.preventDefault();
          const next =
            currentIndex < rowNames.length - 1
              ? currentIndex + 1
              : currentIndex;
          const name = rowNames[next];
          if (name !== undefined) onSelect(name);
          break;
        }
        case "ArrowUp": {
          e.preventDefault();
          const prev = currentIndex > 0 ? currentIndex - 1 : 0;
          const name = rowNames[prev];
          if (name !== undefined) onSelect(name);
          break;
        }
        case "Enter": {
          e.preventDefault();
          if (parsedSelection) {
            const layout = layouts.find(
              (l) => l.name.toLowerCase() === parsedSelection.name.toLowerCase()
            );
            if (layout && layout.spans.some((s) => s.drillable)) {
              onDrillDown(layout.name, parsedSelection.spanIndex ?? undefined);
            }
          }
          break;
        }
        case "Escape": {
          e.preventDefault();
          if (branchPopover) {
            setBranchPopover(null);
          } else {
            onGoUp();
          }
          break;
        }
      }
    },
    [layouts, parsedSelection, onSelect, onDrillDown, onGoUp, branchPopover]
  );

  // Find branches matching the popover's forkedAt UUID.
  // Branches may be on the current node or on any child span in the tree,
  // since markers are collected recursively from the content tree.
  const branchLookup = useMemo(() => {
    if (!branchPopover) return null;
    return findBranchesByForkedAt(node, branchPopover.forkedAt);
  }, [branchPopover, node]);

  const parentRow = layouts[0];
  const childRows = layouts.slice(1);

  const renderRow = (
    layout: RowLayout,
    rowIndex: number,
    displayName?: string
  ) => (
    <SwimlaneRow
      key={`${layout.name}-${rowIndex}`}
      layout={layout}
      displayName={displayName}
      parsedSelection={parsedSelection}
      onSelect={(spanIndex) => {
        if (layout.spans.length > 1) {
          onSelect(layout.name, spanIndex + 1);
        } else {
          onSelect(layout.name);
        }
      }}
      onDrillDown={(spanIndex) =>
        onDrillDown(
          layout.name,
          layout.spans.length > 1 ? spanIndex + 1 : undefined
        )
      }
      onBranchHover={handleBranchHover}
      onBranchLeave={handleBranchLeave}
      showErrorMarkers={showErrorMarkers}
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
      {/* Pinned: breadcrumb (with minimap) + parent row */}
      <div className={styles.pinnedSection}>
        {breadcrumb && <BreadcrumbRow {...breadcrumb} minimap={minimap} />}
      </div>

      {/* Collapsible rows: parent + children */}
      <div
        className={clsx(
          styles.collapsibleSection,
          isCollapsed && styles.collapsibleCollapsed,
          noAnimation && styles.noAnimation
        )}
      >
        <div className={styles.collapsibleInner}>
          <div className={styles.pinnedSection}>
            {parentRow &&
              renderRow(
                parentRow,
                0,
                breadcrumb?.atRoot && parentRow.name === "solvers"
                  ? "main"
                  : undefined
              )}
          </div>
          {childRows.length > 0 && (
            <div className={styles.scrollSection}>
              {childRows.map((layout, i) => renderRow(layout, i + 1))}
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
        onSelect={handleBranchSelect}
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
  parsedSelection: ParsedSelection | null;
  onSelect: (spanIndex: number) => void;
  onDrillDown: (spanIndex: number) => void;
  onBranchHover: (forkedAt: string, element: HTMLElement) => void;
  onBranchLeave: () => void;
  /** Show error markers on swimlane bars. Defaults to false. */
  showErrorMarkers?: boolean;
  onMarkerNavigate?: (eventId: string) => void;
}

const SwimlaneRow: FC<SwimlaneRowProps> = ({
  layout,
  displayName,
  parsedSelection,
  onSelect,
  onDrillDown,
  onBranchHover,
  onBranchLeave,
  showErrorMarkers,
  onMarkerNavigate,
}) => {
  const hasSelectedSpan = layout.spans.some((_, i) =>
    isSpanSelected(layout, i, parsedSelection)
  );

  return (
    <div className={styles.row} role="row">
      {/* Label cell */}
      <div
        className={clsx(
          styles.label,
          !layout.isParent && styles.labelChild,
          hasSelectedSpan && styles.labelSelected
        )}
      >
        {displayName ?? layout.name}
        {layout.parallelCount !== null && (
          <span className={styles.parallelBadge}>({layout.parallelCount})</span>
        )}
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
              isSelected={isSpanSelected(layout, spanIndex, parsedSelection)}
              onSelect={() => onSelect(spanIndex)}
              onDrillDown={() => onDrillDown(spanIndex)}
            />
          ))}

          {/* Markers */}
          {layout.markers.filter((m) => showErrorMarkers || m.kind !== "error").map((marker, i) => (
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
// BreadcrumbRow (internal)
// =============================================================================

interface InternalBreadcrumbRowProps extends BreadcrumbRowProps {
  minimap?: TimelineMinimapProps;
}

const BreadcrumbRow: FC<InternalBreadcrumbRowProps> = ({
  breadcrumbs,
  atRoot,
  onGoUp,
  onNavigate,
  minimap,
  selected,
}) => {
  // Extract display name from selected (strip span index suffix)
  const selectedLabel = selected ? parsePathSegment(selected).name : null;

  // Suppress selection when it duplicates the last breadcrumb (parent row = current node)
  const lastBreadcrumb = breadcrumbs[breadcrumbs.length - 1];
  const showSelection =
    selectedLabel !== null &&
    selectedLabel.toLowerCase() !== lastBreadcrumb?.label.toLowerCase();

  return (
    <div className={styles.breadcrumbRow}>
      <button
        className={styles.breadcrumbBack}
        onClick={onGoUp}
        disabled={atRoot && !showSelection}
        title="Go up one level (Escape)"
      >
        <i className={ApplicationIcons.navbar.back} />
      </button>
      {breadcrumbs.map((segment, i) => {
        const isLast = i === breadcrumbs.length - 1;
        // Show "main" for the root breadcrumb when it's the generic "solvers" name
        const label =
          i === 0 && segment.label === "solvers" ? "main" : segment.label;
        return (
          <span key={segment.path + i} className={styles.breadcrumbGroup}>
            {i > 0 && (
              <span className={styles.breadcrumbDivider}>{"\u203A"}</span>
            )}
            {isLast && !showSelection ? (
              <button
                className={styles.breadcrumbCurrent}
                onClick={() => onNavigate(segment.path)}
              >
                {label}
              </button>
            ) : (
              <button
                className={styles.breadcrumbLink}
                onClick={() => onNavigate(segment.path)}
              >
                {label}
              </button>
            )}
          </span>
        );
      })}
      {showSelection && (
        <span className={styles.breadcrumbGroup}>
          <span className={styles.breadcrumbDivider}>{"\u203A"}</span>
          <span className={styles.breadcrumbSelection}>{selectedLabel}</span>
        </span>
      )}
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
  onDrillDown: () => void;
}

const BarFill: FC<BarFillProps> = ({
  span,
  isParent,
  isSelected,
  onSelect,
  onDrillDown,
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
      if (span.drillable) {
        onDrillDown();
      }
    },
    [span.drillable, onDrillDown]
  );

  const handleChevronClick = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      onDrillDown();
    },
    [onDrillDown]
  );

  return (
    <>
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
        onDoubleClick={handleDoubleClick}
      />
      {span.drillable && (
        <button
          className={styles.drillDown}
          style={{
            left: `${span.bar.left + span.bar.width}%`,
          }}
          onClick={handleChevronClick}
          title={`Drill down (${span.childCount} sub-agent${span.childCount !== 1 ? "s" : ""})`}
        >
          <i className={ApplicationIcons.chevron.right} />
        </button>
      )}
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
// BranchPopover (internal)
// =============================================================================

interface BranchPopoverProps {
  isOpen: boolean;
  anchor: HTMLElement | null;
  branches: Array<{ branch: TimelineBranch; index: number }>;
  onSelect: (branchSegment: string) => void;
  onClose: () => void;
}

const BranchPopover: FC<BranchPopoverProps> = ({
  isOpen,
  anchor,
  branches,
  onSelect,
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
            <button
              key={`branch-${index}`}
              className={styles.branchEntry}
              onClick={() => onSelect(`@branch-${index}`)}
            >
              <span className={styles.branchLabel}>{span.name}</span>
              <span className={styles.branchMeta}>
                {formatTokenCount(branch.totalTokens)}
                {" \u00B7 "}
                {formatTime(durationSec)}
              </span>
            </button>
          );
        })}
      </div>
    </PopOver>
  );
};
