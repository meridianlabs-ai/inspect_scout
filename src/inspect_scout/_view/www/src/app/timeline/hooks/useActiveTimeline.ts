/**
 * Manages which timeline is active when multiple timelines are available.
 *
 * The active timeline is driven by the `timeline_view` URL search param,
 * matched case-insensitively against timeline names. Switching resets the
 * `selected` param (clears swimlane selection).
 */

import { useCallback, useMemo } from "react";
import { useSearchParams } from "react-router-dom";

import type { Timeline } from "../../../components/transcript/timeline";

// =============================================================================
// Constants
// =============================================================================

const kTimelineViewParam = "timeline_view";
const kSelectedParam = "selected";

// =============================================================================
// Types
// =============================================================================

export interface UseActiveTimelineResult {
  /** The currently active Timeline. */
  active: Timeline;
  /** 0-based index of the active timeline. */
  activeIndex: number;
  /** Switch to a different timeline by index. Resets selection. */
  setActive: (index: number) => void;
  /** All available timelines. */
  timelines: Timeline[];
}

// =============================================================================
// Hook
// =============================================================================

export function useActiveTimeline(
  timelines: Timeline[]
): UseActiveTimelineResult {
  const [searchParams, setSearchParams] = useSearchParams();

  const viewParam = searchParams.get(kTimelineViewParam);

  // Resolve active index from URL param (case-insensitive name match)
  const activeIndex = useMemo(() => {
    if (viewParam === null || timelines.length <= 1) return 0;
    const lower = viewParam.toLowerCase();
    const idx = timelines.findIndex((tl) => tl.name.toLowerCase() === lower);
    return idx >= 0 ? idx : 0;
  }, [viewParam, timelines]);

  // Safe access — always falls back to first timeline
  const active = timelines[activeIndex] ?? timelines[0]!;

  const setActive = useCallback(
    (index: number) => {
      if (index < 0 || index >= timelines.length) return;
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          const tl = timelines[index];
          if (tl && timelines.length > 1 && index > 0) {
            next.set(kTimelineViewParam, tl.name);
          } else {
            next.delete(kTimelineViewParam);
          }
          // Reset selection when switching timelines
          next.delete(kSelectedParam);
          return next;
        },
        { replace: true }
      );
    },
    [setSearchParams, timelines]
  );

  return { active, activeIndex, setActive, timelines };
}
