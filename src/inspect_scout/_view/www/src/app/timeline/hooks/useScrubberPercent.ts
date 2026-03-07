/**
 * Returns the scroll progress (0–1) within the virtual event list.
 *
 * The minimap uses this to position the scrubber as a fraction of the
 * selection bar — completely decoupled from event timestamps, which are
 * non-monotonic in the depth-first flattened list.
 */

import { useStore } from "../../../state/store";

export function useScrubberProgress(listKey: string): number | null {
  const visibleRange = useStore((state) => state.visibleRanges[listKey]);

  if (!visibleRange) return null;

  const { startIndex, endIndex, totalCount } = visibleRange;
  if (totalCount <= 1) return null;

  // The scrollable range is 0..totalCount-viewportSize (not 0..totalCount-1),
  // because at the bottom of scroll startIndex is totalCount - viewportSize,
  // not totalCount - 1. Dividing by the actual scrollable range gives 0–1.
  const viewportSize = endIndex - startIndex;
  const maxStartIndex = totalCount - 1 - viewportSize;
  if (maxStartIndex <= 0) return null;

  return Math.min(1, Math.max(0, startIndex / maxStartIndex));
}
