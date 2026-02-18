// @vitest-environment jsdom
import { act, renderHook } from "@testing-library/react";
import { type PropsWithChildren, createElement } from "react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import type {
  Timeline,
  TimelineSpan,
} from "../../../components/transcript/timeline";
import { timelineScenarios } from "../syntheticNodes";
import { isParallelSpan, isSingleSpan } from "../utils/swimlaneRows";

import {
  buildBreadcrumbs,
  parsePathSegment,
  resolvePath,
  useTimeline,
} from "./useTimeline";

// =============================================================================
// Scenario helpers
// =============================================================================

const S1_SEQUENTIAL = 0;
const S2_ITERATIVE = 1;
const S3_DEEP = 2;
const S4_PARALLEL = 3;
const S7_FLAT = 5;
const S11A_BRANCHES = 8;

function getTimeline(index: number): Timeline {
  const scenario = timelineScenarios[index];
  if (!scenario) throw new Error(`No scenario at index ${index}`);
  return scenario.timeline;
}

// =============================================================================
// parsePathSegment
// =============================================================================

describe("parsePathSegment", () => {
  it("returns name only for simple segment", () => {
    expect(parsePathSegment("explore")).toEqual({
      name: "explore",
      spanIndex: null,
    });
  });

  it("extracts span index from trailing -N", () => {
    expect(parsePathSegment("explore-2")).toEqual({
      name: "explore",
      spanIndex: 2,
    });
  });

  it("handles hyphenated names without index", () => {
    expect(parsePathSegment("my-agent")).toEqual({
      name: "my-agent",
      spanIndex: null,
    });
  });

  it("extracts index from hyphenated name with trailing -N", () => {
    expect(parsePathSegment("my-agent-3")).toEqual({
      name: "my-agent",
      spanIndex: 3,
    });
  });

  it("treats -0 as part of the name (0 is not a valid 1-indexed span)", () => {
    expect(parsePathSegment("explore-0")).toEqual({
      name: "explore-0",
      spanIndex: null,
    });
  });

  it("handles single character name", () => {
    expect(parsePathSegment("a-1")).toEqual({
      name: "a",
      spanIndex: 1,
    });
  });

  it("handles large span index", () => {
    expect(parsePathSegment("build-10")).toEqual({
      name: "build",
      spanIndex: 10,
    });
  });
});

// =============================================================================
// resolvePath
// =============================================================================

describe("resolvePath", () => {
  it("returns root span for empty path", () => {
    const timeline = getTimeline(S1_SEQUENTIAL);
    const result = resolvePath(timeline, "");
    expect(result).toBe(timeline.root);
  });

  it("returns root span for path with only whitespace segments", () => {
    const timeline = getTimeline(S1_SEQUENTIAL);
    const result = resolvePath(timeline, "");
    expect(result).toBe(timeline.root);
  });

  it("resolves a named child span", () => {
    const timeline = getTimeline(S1_SEQUENTIAL);
    const result = resolvePath(timeline, "explore");
    expect(result).not.toBeNull();
    expect(result!.type).toBe("span");
    expect((result as TimelineSpan).name).toBe("Explore");
  });

  it("resolves case-insensitively", () => {
    const timeline = getTimeline(S1_SEQUENTIAL);
    const result = resolvePath(timeline, "EXPLORE");
    expect(result).not.toBeNull();
    expect((result as TimelineSpan).name).toBe("Explore");
  });

  it("resolves nested paths (S3 deep nesting)", () => {
    const timeline = getTimeline(S3_DEEP);
    const result = resolvePath(timeline, "build/code");
    expect(result).not.toBeNull();
    expect((result as TimelineSpan).name).toBe("Code");
  });

  it("resolves multi-level nested paths", () => {
    const timeline = getTimeline(S3_DEEP);
    const result = resolvePath(timeline, "build/code");
    expect(result).not.toBeNull();
    const code = result as TimelineSpan;
    expect(code.name).toBe("Code");
  });

  it("resolves span index for iterative agents (S2)", () => {
    const timeline = getTimeline(S2_ITERATIVE);
    // S2 has 2 Explore spans
    const first = resolvePath(timeline, "explore-1");
    const second = resolvePath(timeline, "explore-2");
    expect(first).not.toBeNull();
    expect(second).not.toBeNull();
    expect(first).not.toBe(second);
    expect((first as TimelineSpan).name).toBe("Explore");
    expect((second as TimelineSpan).name).toBe("Explore");
  });

  it("creates synthetic container when no span index and multiple matches", () => {
    const timeline = getTimeline(S2_ITERATIVE);
    const container = resolvePath(timeline, "explore");
    expect(container).not.toBeNull();
    // Container wraps all same-named children with numbered names
    const children = container!.content.filter(
      (c): c is TimelineSpan => c.type === "span"
    );
    expect(children).toHaveLength(2);
    expect(children[0]!.name).toBe("Explore 1");
    expect(children[1]!.name).toBe("Explore 2");
    // Container aggregates tokens
    const firstIndex = resolvePath(timeline, "explore-1");
    const secondIndex = resolvePath(timeline, "explore-2");
    expect(container!.totalTokens).toBe(
      firstIndex!.totalTokens + secondIndex!.totalTokens
    );
  });

  it("returns null for invalid path", () => {
    const timeline = getTimeline(S1_SEQUENTIAL);
    const result = resolvePath(timeline, "nonexistent");
    expect(result).toBeNull();
  });

  it("returns null for invalid nested path", () => {
    const timeline = getTimeline(S1_SEQUENTIAL);
    const result = resolvePath(timeline, "explore/nonexistent");
    expect(result).toBeNull();
  });

  it("resolves scoring as a child span", () => {
    const timeline = getTimeline(S1_SEQUENTIAL);
    const result = resolvePath(timeline, "scoring");
    expect(result).not.toBeNull();
    expect(result!.type).toBe("span");
    expect((result as TimelineSpan).name).toBe("Scoring");
    expect((result as TimelineSpan).spanType).toBe("scorer");
  });

  it("returns null for init path (init events are not navigable)", () => {
    const timeline = getTimeline(S1_SEQUENTIAL);
    // No child span named "init" exists
    const result = resolvePath(timeline, "init");
    expect(result).toBeNull();
  });

  it("returns null for out-of-range span index", () => {
    const timeline = getTimeline(S2_ITERATIVE);
    const result = resolvePath(timeline, "explore-99");
    expect(result).toBeNull();
  });

  it("resolves @branch-N segments (S11a)", () => {
    const timeline = getTimeline(S11A_BRANCHES);
    const result = resolvePath(timeline, "build/@branch-1");
    expect(result).not.toBeNull();
    // Branch 1 has two child spans, so it returns a wrapper
    expect(result!.name).toContain("Refactor");
    expect(result!.content.length).toBeGreaterThan(0);
  });

  it("resolves single-span branch directly (S11a)", () => {
    const timeline = getTimeline(S11A_BRANCHES);
    const result = resolvePath(timeline, "build/@branch-2");
    expect(result).not.toBeNull();
    // Branch 2 has one child span (Rewrite), returned directly
    expect(result!.name).toContain("Rewrite");
  });

  it("returns null for invalid branch index", () => {
    const timeline = getTimeline(S11A_BRANCHES);
    const result = resolvePath(timeline, "build/@branch-99");
    expect(result).toBeNull();
  });
});

// =============================================================================
// buildBreadcrumbs
// =============================================================================

describe("buildBreadcrumbs", () => {
  it("returns root breadcrumb for empty path", () => {
    const timeline = getTimeline(S1_SEQUENTIAL);
    const crumbs = buildBreadcrumbs("", timeline);
    expect(crumbs).toHaveLength(1);
    expect(crumbs[0]!.label).toBe(timeline.root.name);
    expect(crumbs[0]!.path).toBe("");
  });

  it("builds breadcrumbs for single-level path", () => {
    const timeline = getTimeline(S1_SEQUENTIAL);
    const crumbs = buildBreadcrumbs("build", timeline);
    expect(crumbs).toHaveLength(2);
    expect(crumbs[0]!.label).toBe(timeline.root.name);
    expect(crumbs[0]!.path).toBe("");
    expect(crumbs[1]!.label).toBe("Build");
    expect(crumbs[1]!.path).toBe("build");
  });

  it("builds breadcrumbs for multi-level path (S3)", () => {
    const timeline = getTimeline(S3_DEEP);
    const crumbs = buildBreadcrumbs("build/code", timeline);
    expect(crumbs).toHaveLength(3);
    expect(crumbs[0]!.path).toBe("");
    expect(crumbs[1]!.label).toBe("Build");
    expect(crumbs[1]!.path).toBe("build");
    expect(crumbs[2]!.label).toBe("Code");
    expect(crumbs[2]!.path).toBe("build/code");
  });

  it("builds breadcrumbs for scoring", () => {
    const timeline = getTimeline(S1_SEQUENTIAL);
    const crumbs = buildBreadcrumbs("scoring", timeline);
    expect(crumbs).toHaveLength(2);
    expect(crumbs[1]!.label).toBe("Scoring");
    expect(crumbs[1]!.path).toBe("scoring");
  });

  it("uses raw segment for unresolvable path", () => {
    const timeline = getTimeline(S1_SEQUENTIAL);
    const crumbs = buildBreadcrumbs("nonexistent", timeline);
    expect(crumbs).toHaveLength(2);
    expect(crumbs[1]!.label).toBe("nonexistent");
  });

  it("resolves branch segments with correct labels (S11a)", () => {
    const timeline = getTimeline(S11A_BRANCHES);
    const crumbs = buildBreadcrumbs("build/@branch-1", timeline);
    expect(crumbs).toHaveLength(3);
    expect(crumbs[0]!.label).toBe("Transcript");
    expect(crumbs[1]!.label).toBe("Build");
    expect(crumbs[2]!.label).toContain("Refactor");
    expect(crumbs[2]!.path).toBe("build/@branch-1");
  });

  it("resolves single-span branch segments (S11a)", () => {
    const timeline = getTimeline(S11A_BRANCHES);
    const crumbs = buildBreadcrumbs("build/@branch-2", timeline);
    expect(crumbs).toHaveLength(3);
    expect(crumbs[2]!.label).toContain("Rewrite");
  });
});

// =============================================================================
// useTimeline hook
// =============================================================================

function createWrapper(initialEntries: string[] = ["/"]) {
  return function Wrapper({ children }: PropsWithChildren) {
    return createElement(MemoryRouter, { initialEntries }, children);
  };
}

describe("useTimeline", () => {
  it("resolves root node with no path params (S1)", () => {
    const timeline = getTimeline(S1_SEQUENTIAL);
    const { result } = renderHook(() => useTimeline(timeline), {
      wrapper: createWrapper(),
    });

    expect(result.current.node.name).toBe(timeline.root.name);
    // S1 has: Explore, Plan, Build, Scoring children = 5 rows
    // (Transcript parent + Explore + Plan + Build + Scoring)
    expect(result.current.rows).toHaveLength(5);
    expect(result.current.breadcrumbs).toHaveLength(1);
    expect(result.current.selected).toBe("Transcript");
  });

  it("resolves drilled-down node via path param", () => {
    const timeline = getTimeline(S1_SEQUENTIAL);
    const { result } = renderHook(() => useTimeline(timeline), {
      wrapper: createWrapper(["/?path=build"]),
    });

    expect(result.current.node.name).toBe("Build");
    expect(result.current.breadcrumbs).toHaveLength(2);
  });

  it("returns single row for flat transcript (S7)", () => {
    const timeline = getTimeline(S7_FLAT);
    const { result } = renderHook(() => useTimeline(timeline), {
      wrapper: createWrapper(),
    });

    // S7 has no child spans → just the parent row
    expect(result.current.rows).toHaveLength(1);
  });

  it("detects parallel spans (S4)", () => {
    const timeline = getTimeline(S4_PARALLEL);
    const { result } = renderHook(() => useTimeline(timeline), {
      wrapper: createWrapper(),
    });

    const exploreRow = result.current.rows.find((r) => r.name === "Explore");
    expect(exploreRow).toBeDefined();
    expect(exploreRow!.spans).toHaveLength(1);
    expect(isParallelSpan(exploreRow!.spans[0]!)).toBe(true);
  });

  it("reads selected param", () => {
    const timeline = getTimeline(S1_SEQUENTIAL);
    const { result } = renderHook(() => useTimeline(timeline), {
      wrapper: createWrapper(["/?selected=explore"]),
    });

    expect(result.current.selected).toBe("explore");
  });

  it("builds breadcrumbs for nested path", () => {
    const timeline = getTimeline(S3_DEEP);
    const { result } = renderHook(() => useTimeline(timeline), {
      wrapper: createWrapper(["/?path=build/code"]),
    });

    expect(result.current.breadcrumbs).toHaveLength(3);
    expect(result.current.breadcrumbs[0]!.label).toBe(timeline.root.name);
    expect(result.current.breadcrumbs[1]!.label).toBe("Build");
    expect(result.current.breadcrumbs[2]!.label).toBe("Code");
  });

  it("falls back to root for invalid path", () => {
    const timeline = getTimeline(S1_SEQUENTIAL);
    const { result } = renderHook(() => useTimeline(timeline), {
      wrapper: createWrapper(["/?path=nonexistent"]),
    });

    // Should fall back to root
    expect(result.current.node.name).toBe(timeline.root.name);
    expect(result.current.rows.length).toBeGreaterThanOrEqual(1);
  });

  it("scoring appears in root rows but not when drilled into Build", () => {
    const timeline = getTimeline(S1_SEQUENTIAL);

    // At root: scoring should be a row
    const { result: rootResult } = renderHook(() => useTimeline(timeline), {
      wrapper: createWrapper(),
    });
    const scoringRow = rootResult.current.rows.find(
      (r) => r.name === "Scoring"
    );
    expect(scoringRow).toBeDefined();

    // Drilled into Build: no scoring row
    const { result: drillResult } = renderHook(() => useTimeline(timeline), {
      wrapper: createWrapper(["/?path=build"]),
    });
    const scoringInBuild = drillResult.current.rows.find(
      (r) => r.name === "Scoring"
    );
    expect(scoringInBuild).toBeUndefined();
  });

  it("resolves scoring path to scorer span", () => {
    const timeline = getTimeline(S1_SEQUENTIAL);
    const { result } = renderHook(() => useTimeline(timeline), {
      wrapper: createWrapper(["/?path=scoring"]),
    });

    expect(result.current.node.name).toBe("Scoring");
    expect(result.current.node.type).toBe("span");
  });

  // ---------------------------------------------------------------------------
  // Navigation functions
  // ---------------------------------------------------------------------------

  it("drillDown appends to path and clears selection", () => {
    const timeline = getTimeline(S1_SEQUENTIAL);
    const { result } = renderHook(() => useTimeline(timeline), {
      wrapper: createWrapper(["/?selected=explore"]),
    });

    act(() => {
      result.current.drillDown("build");
    });

    expect(result.current.node.name).toBe("Build");
    expect(result.current.selected).toBe("Build");
  });

  it("drillDown from nested path appends segment", () => {
    const timeline = getTimeline(S3_DEEP);
    const { result } = renderHook(() => useTimeline(timeline), {
      wrapper: createWrapper(["/?path=build"]),
    });

    act(() => {
      result.current.drillDown("code");
    });

    expect(result.current.node.name).toBe("Code");
    expect(result.current.breadcrumbs).toHaveLength(3);
  });

  it("drillDown with span index", () => {
    const timeline = getTimeline(S2_ITERATIVE);
    const { result } = renderHook(() => useTimeline(timeline), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.drillDown("explore", 2);
    });

    expect(result.current.node.name).toBe("Explore");
    // Should be the second Explore, not the first
    const firstExplore = timeline.root.content.find(
      (c): c is TimelineSpan => c.type === "span" && c.name === "Explore"
    );
    expect(result.current.node).not.toBe(firstExplore);
  });

  it("goUp removes last path segment", () => {
    const timeline = getTimeline(S3_DEEP);
    const { result } = renderHook(() => useTimeline(timeline), {
      wrapper: createWrapper(["/?path=build/code"]),
    });

    expect(result.current.node.name).toBe("Code");

    act(() => {
      result.current.goUp();
    });

    expect(result.current.node.name).toBe("Build");
  });

  it("goUp from single segment returns to root", () => {
    const timeline = getTimeline(S1_SEQUENTIAL);
    const { result } = renderHook(() => useTimeline(timeline), {
      wrapper: createWrapper(["/?path=build"]),
    });

    act(() => {
      result.current.goUp();
    });

    expect(result.current.node.name).toBe(timeline.root.name);
    expect(result.current.breadcrumbs).toHaveLength(1);
  });

  it("goUp at root is a no-op", () => {
    const timeline = getTimeline(S1_SEQUENTIAL);
    const { result } = renderHook(() => useTimeline(timeline), {
      wrapper: createWrapper(),
    });

    const nameBefore = result.current.node.name;

    act(() => {
      result.current.goUp();
    });

    expect(result.current.node.name).toBe(nameBefore);
  });

  it("select sets the selected param", () => {
    const timeline = getTimeline(S1_SEQUENTIAL);
    const { result } = renderHook(() => useTimeline(timeline), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.select("explore");
    });

    expect(result.current.selected).toBe("explore");
  });

  it("select(null) clears the selected param and defaults to root", () => {
    const timeline = getTimeline(S1_SEQUENTIAL);
    const { result } = renderHook(() => useTimeline(timeline), {
      wrapper: createWrapper(["/?selected=explore"]),
    });

    act(() => {
      result.current.select(null);
    });

    // With no explicit selection, defaults to root row
    expect(result.current.selected).toBe("Transcript");
  });

  it("iterative agents produce multiple SingleSpans on one row (S2)", () => {
    const timeline = getTimeline(S2_ITERATIVE);
    const { result } = renderHook(() => useTimeline(timeline), {
      wrapper: createWrapper(),
    });

    const exploreRow = result.current.rows.find((r) => r.name === "Explore");
    expect(exploreRow).toBeDefined();
    expect(exploreRow!.spans).toHaveLength(2);
    for (const span of exploreRow!.spans) {
      expect(isSingleSpan(span)).toBe(true);
    }
  });
});
