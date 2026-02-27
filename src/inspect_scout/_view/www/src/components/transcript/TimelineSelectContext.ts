import { createContext, useContext } from "react";

/**
 * Selects a swimlane row by span ID. The provider maps the ID to the
 * correct (name, spanIndex) pair needed by the timeline state.
 */
export type TimelineSelectByIdFn = (spanId: string) => void;

export const TimelineSelectContext = createContext<TimelineSelectByIdFn | null>(
  null
);

export function useTimelineSelect(): TimelineSelectByIdFn | null {
  return useContext(TimelineSelectContext);
}
