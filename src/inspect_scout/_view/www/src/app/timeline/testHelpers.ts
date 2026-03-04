/**
 * Shared test utilities for timeline tests.
 *
 * Provides common helpers used across swimlaneRows, swimlaneLayout,
 * markers, and useTimeline test files.
 */

import type {
  Timeline,
  TimelineBranch,
  TimelineSpan,
} from "../../components/transcript/timeline";

import { timelineScenarios } from "./syntheticNodes";

export { timelineScenarios };

// =============================================================================
// Timestamp helper
// =============================================================================

const BASE = new Date("2025-01-15T10:00:00Z").getTime();

/** Creates a Date offset from a fixed base time by the given number of seconds. */
export function ts(offsetSeconds: number): Date {
  return new Date(BASE + offsetSeconds * 1000);
}

// =============================================================================
// Span builder
// =============================================================================

interface MakeSpanOptions {
  utility?: boolean;
  spanType?: string | null;
  branches?: TimelineBranch[];
}

/** Minimal TimelineSpan builder for edge-case tests. */
export function makeSpan(
  name: string,
  startSec: number,
  endSec: number,
  tokens: number,
  content: TimelineSpan["content"] = [],
  options?: MakeSpanOptions
): TimelineSpan {
  return {
    type: "span",
    id: name.toLowerCase(),
    name,
    spanType: options?.spanType ?? null,
    content,
    branches: options?.branches ?? [],
    utility: options?.utility ?? false,
    startTime: ts(startSec),
    endTime: ts(endSec),
    totalTokens: tokens,
  };
}

// =============================================================================
// Scenario index constants
// =============================================================================

export const S1_SEQUENTIAL = 0;
export const S2_ITERATIVE = 1;
export const S3_DEEP = 2;
export const S4_PARALLEL = 3;
export const S5_MARKERS = 4;
export const S7_FLAT = 5;
export const S8_MANY = 6;
export const S10_UTILITY = 7;
export const S11A_BRANCHES = 8;

// =============================================================================
// Scenario lookup helpers
// =============================================================================

/** Returns the root TimelineSpan for a scenario by index. */
export function getScenarioRoot(index: number): TimelineSpan {
  const scenario = timelineScenarios[index];
  if (!scenario) throw new Error(`No scenario at index ${index}`);
  return scenario.timeline.root;
}

/** Returns the full Timeline for a scenario by index. */
export function getTimeline(index: number): Timeline {
  const scenario = timelineScenarios[index];
  if (!scenario) throw new Error(`No scenario at index ${index}`);
  return scenario.timeline;
}
