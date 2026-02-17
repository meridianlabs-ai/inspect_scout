import clsx from "clsx";
import { FC, useCallback, useMemo, useState } from "react";

import { ApplicationIcons } from "../../components/icons";
import { PopOver } from "../../components/PopOver";
import type {
  TimelineBranch,
  TimelineSpan,
} from "../../components/transcript/timeline";
import { useProperty } from "../../state/hooks/useProperty";
import { formatTime } from "../../utils/format";

import type {
  PositionedMarker,
  PositionedSpan,
  RowLayout,
} from "./swimlaneLayout";
import { formatTokenCount } from "./swimlaneLayout";
import styles from "./SwimLanePanel.module.css";
import { TimelineMinimap, type TimelineMinimapProps } from "./TimelineMinimap";
import {
  type BreadcrumbSegment,
  createBranchSpan,
  parsePathSegment,
} from "./useTimeline";

// =============================================================================
// Types
// =============================================================================

interface SwimLanePanelProps {
  /** Row layouts computed by computeRowLayouts. */
  layouts: RowLayout[];
  /** Currently selected span identifier (e.g. "explore" or "explore-2"), or null. */
  selected: string | null;
  /** The current drill-down node (for branch lookup). */
  node: TimelineSpan;
  /** Called when a span is clicked (selection). */
  onSelect: (name: string, spanIndex?: number) => void;
  /** Called when a span's drill-down chevron is clicked. */
  onDrillDown: (name: string, spanIndex?: number) => void;
  /** Called when a branch popover entry is clicked. Segment is e.g. "@branch-1". */
  onBranchDrillDown: (branchSegment: string) => void;
  /** Called on Escape key (go up). */
  onGoUp: () => void;
  /** Minimap props for the zoom indicator row. */
  minimap?: TimelineMinimapProps;
  /** Breadcrumb props for the navigation row. */
  breadcrumb?: BreadcrumbRowProps;
}

interface BreadcrumbRowProps {
  breadcrumbs: BreadcrumbSegment[];
  atRoot: boolean;
  onGoUp: () => void;
  onNavigate: (path: string) => void;
  minimap?: TimelineMinimapProps;
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

const MARKER_GLYPHS: Record<string, string> = {
  error: "\u25B2", // ▲
  compaction: "\u250A", // ┊
  branch: "\u21B3", // ↳
};

// =============================================================================
// SwimLanePanel
// =============================================================================

export const SwimLanePanel: FC<SwimLanePanelProps> = ({
  layouts,
  selected,
  node,
  onSelect,
  onDrillDown,
  onBranchDrillDown,
  onGoUp,
  minimap,
  breadcrumb,
}) => {
  const parsedSelection = useMemo(() => parseSelected(selected), [selected]);

  // Collapse state — persisted across sessions
  const [collapsed, setCollapsed] = useProperty<boolean>(
    "timeline",
    "swimlanesCollapsed",
    { defaultValue: false, cleanup: false }
  );
  const isCollapsed = !!collapsed;
  const toggleCollapsed = useCallback(() => {
    setCollapsed(!isCollapsed);
  }, [isCollapsed, setCollapsed]);

  // Branch popover state
  const [branchPopover, setBranchPopover] = useState<{
    forkedAt: string;
    element: HTMLElement;
  } | null>(null);

  const handleBranchClick = useCallback(
    (forkedAt: string, element: HTMLElement) => {
      setBranchPopover((prev) =>
        prev?.forkedAt === forkedAt ? null : { forkedAt, element }
      );
    },
    []
  );

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
        onBranchDrillDown(fullSegment);
      } else {
        onBranchDrillDown(branchSegment);
      }
    },
    [onBranchDrillDown, node, branchPopover?.forkedAt]
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

  const renderRow = (layout: RowLayout, rowIndex: number) => (
    <SwimLaneRow
      key={`${layout.name}-${rowIndex}`}
      layout={layout}
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
      onBranchClick={handleBranchClick}
    />
  );

  return (
    <div
      className={styles.swimlane}
      tabIndex={0}
      onKeyDown={handleKeyDown}
      role="grid"
      aria-label="Timeline swimlane"
    >
      {/* Pinned: breadcrumb (with minimap) + parent row */}
      <div className={styles.pinnedSection}>
        {breadcrumb && <BreadcrumbRow {...breadcrumb} minimap={minimap} />}
        {!isCollapsed && parentRow && renderRow(parentRow, 0)}
      </div>

      {/* Scrollable: child rows */}
      {!isCollapsed && childRows.length > 0 && (
        <div className={styles.scrollSection}>
          {childRows.map((layout, i) => renderRow(layout, i + 1))}
        </div>
      )}

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
// SwimLaneRow (internal)
// =============================================================================

interface SwimLaneRowProps {
  layout: RowLayout;
  parsedSelection: ParsedSelection | null;
  onSelect: (spanIndex: number) => void;
  onDrillDown: (spanIndex: number) => void;
  onBranchClick: (forkedAt: string, element: HTMLElement) => void;
}

const SwimLaneRow: FC<SwimLaneRowProps> = ({
  layout,
  parsedSelection,
  onSelect,
  onDrillDown,
  onBranchClick,
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
        {layout.name}
        {layout.parallelCount !== null && (
          <span className={styles.parallelBadge}>({layout.parallelCount})</span>
        )}
      </div>

      {/* Bar area cell */}
      <div className={styles.barArea}>
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
        {layout.markers.map((marker, i) => (
          <MarkerGlyph key={i} marker={marker} onBranchClick={onBranchClick} />
        ))}
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

const BreadcrumbRow: FC<BreadcrumbRowProps> = ({
  breadcrumbs,
  atRoot,
  onGoUp,
  onNavigate,
  minimap,
}) => {
  return (
    <div className={styles.breadcrumbRow}>
      <button
        className={styles.breadcrumbBack}
        onClick={onGoUp}
        disabled={atRoot}
        title="Go up one level (Escape)"
      >
        <i className={ApplicationIcons.navbar.back} />
      </button>
      {breadcrumbs.map((segment, i) => {
        const isLast = i === breadcrumbs.length - 1;
        return (
          <span key={segment.path + i} className={styles.breadcrumbGroup}>
            {i > 0 && (
              <span className={styles.breadcrumbDivider}>{"\u203A"}</span>
            )}
            {isLast ? (
              <span className={styles.breadcrumbCurrent}>{segment.label}</span>
            ) : (
              <button
                className={styles.breadcrumbLink}
                onClick={() => onNavigate(segment.path)}
              >
                {segment.label}
              </button>
            )}
          </span>
        );
      })}
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
          className={styles.chevron}
          style={{
            left: `${span.bar.left + span.bar.width}%`,
          }}
          onClick={handleChevronClick}
          title="Drill down"
        >
          {"\u203A"}
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
  onBranchClick: (forkedAt: string, element: HTMLElement) => void;
}

const MarkerGlyph: FC<MarkerGlyphProps> = ({ marker, onBranchClick }) => {
  const glyph = MARKER_GLYPHS[marker.kind] ?? "?";
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
        onBranchClick(marker.reference, e.currentTarget);
      }
    },
    [marker.kind, marker.reference, onBranchClick]
  );

  return (
    <span
      className={clsx(styles.marker, kindClass)}
      style={{ left: `${marker.left}%` }}
      title={marker.kind === "branch" ? "View branches" : marker.kind}
      onClick={handleClick}
    >
      {glyph}
    </span>
  );
};

// =============================================================================
// Branch lookup helpers
// =============================================================================

interface BranchLookupResult {
  /** The span that owns the branches. */
  owner: TimelineSpan;
  /** Path segments from the search root to the owner (empty if owner is root). */
  ownerPath: string[];
  /** Matching branches with their 1-indexed position. */
  branches: Array<{ branch: TimelineBranch; index: number }>;
}

/**
 * Finds all branches matching a forkedAt UUID anywhere in the span tree.
 * Returns the owning span, its path from root, and matching branches.
 */
function findBranchesByForkedAt(
  node: TimelineSpan,
  forkedAt: string,
  pathSoFar: string[] = []
): BranchLookupResult | null {
  // Check this node's branches
  const matches: Array<{ branch: TimelineBranch; index: number }> = [];
  for (let i = 0; i < node.branches.length; i++) {
    const branch = node.branches[i]!;
    if (branch.forkedAt === forkedAt) {
      matches.push({ branch, index: i + 1 });
    }
  }
  if (matches.length > 0) {
    return { owner: node, ownerPath: pathSoFar, branches: matches };
  }

  // Recurse into child spans
  for (const item of node.content) {
    if (item.type === "span") {
      const found = findBranchesByForkedAt(item, forkedAt, [
        ...pathSoFar,
        item.name.toLowerCase(),
      ]);
      if (found) return found;
    }
  }

  return null;
}

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
      hoverDelay={-1}
      closeOnMouseLeave={false}
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
