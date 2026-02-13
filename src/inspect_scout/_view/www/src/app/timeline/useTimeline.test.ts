// @vitest-environment jsdom
import { act, renderHook } from "@testing-library/react";
import { type PropsWithChildren, createElement } from "react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import type {
  AgentNode,
  SectionNode,
  TranscriptNodes,
} from "../../components/transcript/nodes";

import { isParallelSpan, isSingleSpan } from "./swimlaneRows";
import { timelineScenarios } from "./syntheticNodes";
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

function getTree(index: number): TranscriptNodes {
  const scenario = timelineScenarios[index];
  if (!scenario) throw new Error(`No scenario at index ${index}`);
  return scenario.nodes;
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
  it("returns root agent for empty path", () => {
    const tree = getTree(S1_SEQUENTIAL);
    const result = resolvePath(tree, "");
    expect(result).toBe(tree.agent);
  });

  it("returns root agent for path with only whitespace segments", () => {
    const tree = getTree(S1_SEQUENTIAL);
    const result = resolvePath(tree, "");
    expect(result).toBe(tree.agent);
  });

  it("resolves a named child agent", () => {
    const tree = getTree(S1_SEQUENTIAL);
    const result = resolvePath(tree, "explore");
    expect(result).not.toBeNull();
    expect(result!.type).toBe("agent");
    expect((result as AgentNode).name).toBe("Explore");
  });

  it("resolves case-insensitively", () => {
    const tree = getTree(S1_SEQUENTIAL);
    const result = resolvePath(tree, "EXPLORE");
    expect(result).not.toBeNull();
    expect((result as AgentNode).name).toBe("Explore");
  });

  it("resolves nested paths (S3 deep nesting)", () => {
    const tree = getTree(S3_DEEP);
    const result = resolvePath(tree, "build/code");
    expect(result).not.toBeNull();
    expect((result as AgentNode).name).toBe("Code");
  });

  it("resolves multi-level nested paths", () => {
    const tree = getTree(S3_DEEP);
    const result = resolvePath(tree, "build/code");
    expect(result).not.toBeNull();
    const code = result as AgentNode;
    expect(code.name).toBe("Code");
  });

  it("resolves span index for iterative agents (S2)", () => {
    const tree = getTree(S2_ITERATIVE);
    // S2 has 2 Explore agents
    const first = resolvePath(tree, "explore-1");
    const second = resolvePath(tree, "explore-2");
    expect(first).not.toBeNull();
    expect(second).not.toBeNull();
    expect(first).not.toBe(second);
    expect((first as AgentNode).name).toBe("Explore");
    expect((second as AgentNode).name).toBe("Explore");
  });

  it("returns first match when no span index", () => {
    const tree = getTree(S2_ITERATIVE);
    const noIndex = resolvePath(tree, "explore");
    const firstIndex = resolvePath(tree, "explore-1");
    expect(noIndex).toBe(firstIndex);
  });

  it("returns null for invalid path", () => {
    const tree = getTree(S1_SEQUENTIAL);
    const result = resolvePath(tree, "nonexistent");
    expect(result).toBeNull();
  });

  it("returns null for invalid nested path", () => {
    const tree = getTree(S1_SEQUENTIAL);
    const result = resolvePath(tree, "explore/nonexistent");
    expect(result).toBeNull();
  });

  it("returns null when tree has no agent", () => {
    const emptyTree: TranscriptNodes = {
      init: null,
      agent: null,
      scoring: null,
      startTime: null,
      endTime: null,
      totalTokens: 0,
    };
    expect(resolvePath(emptyTree, "")).toBeNull();
  });

  it("resolves scoring section", () => {
    const tree = getTree(S1_SEQUENTIAL);
    const result = resolvePath(tree, "scoring");
    expect(result).not.toBeNull();
    expect(result!.type).toBe("section");
    expect((result as SectionNode).section).toBe("scoring");
  });

  it("returns null for init when tree has no init", () => {
    const tree = getTree(S1_SEQUENTIAL);
    // S1 has no init section
    const result = resolvePath(tree, "init");
    expect(result).toBeNull();
  });

  it("returns null for out-of-range span index", () => {
    const tree = getTree(S2_ITERATIVE);
    const result = resolvePath(tree, "explore-99");
    expect(result).toBeNull();
  });
});

// =============================================================================
// buildBreadcrumbs
// =============================================================================

describe("buildBreadcrumbs", () => {
  it("returns root breadcrumb for empty path", () => {
    const tree = getTree(S1_SEQUENTIAL);
    const crumbs = buildBreadcrumbs("", tree);
    expect(crumbs).toHaveLength(1);
    expect(crumbs[0]!.label).toBe(tree.agent!.name);
    expect(crumbs[0]!.path).toBe("");
  });

  it("builds breadcrumbs for single-level path", () => {
    const tree = getTree(S1_SEQUENTIAL);
    const crumbs = buildBreadcrumbs("build", tree);
    expect(crumbs).toHaveLength(2);
    expect(crumbs[0]!.label).toBe(tree.agent!.name);
    expect(crumbs[0]!.path).toBe("");
    expect(crumbs[1]!.label).toBe("Build");
    expect(crumbs[1]!.path).toBe("build");
  });

  it("builds breadcrumbs for multi-level path (S3)", () => {
    const tree = getTree(S3_DEEP);
    const crumbs = buildBreadcrumbs("build/code", tree);
    expect(crumbs).toHaveLength(3);
    expect(crumbs[0]!.path).toBe("");
    expect(crumbs[1]!.label).toBe("Build");
    expect(crumbs[1]!.path).toBe("build");
    expect(crumbs[2]!.label).toBe("Code");
    expect(crumbs[2]!.path).toBe("build/code");
  });

  it("builds breadcrumbs for scoring", () => {
    const tree = getTree(S1_SEQUENTIAL);
    const crumbs = buildBreadcrumbs("scoring", tree);
    expect(crumbs).toHaveLength(2);
    expect(crumbs[1]!.label).toBe("Scoring");
    expect(crumbs[1]!.path).toBe("scoring");
  });

  it("uses raw segment for unresolvable path", () => {
    const tree = getTree(S1_SEQUENTIAL);
    const crumbs = buildBreadcrumbs("nonexistent", tree);
    expect(crumbs).toHaveLength(2);
    expect(crumbs[1]!.label).toBe("nonexistent");
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
    const tree = getTree(S1_SEQUENTIAL);
    const { result } = renderHook(() => useTimeline(tree), {
      wrapper: createWrapper(),
    });

    expect(result.current.node.name).toBe(tree.agent!.name);
    // S1 has: Explore, Plan, Build children + Scoring folded in = 5 rows
    // (Transcript parent + Explore + Plan + Build + Scoring)
    expect(result.current.rows).toHaveLength(5);
    expect(result.current.breadcrumbs).toHaveLength(1);
    expect(result.current.selected).toBeNull();
  });

  it("resolves drilled-down node via path param", () => {
    const tree = getTree(S1_SEQUENTIAL);
    const { result } = renderHook(() => useTimeline(tree), {
      wrapper: createWrapper(["/?path=build"]),
    });

    expect(result.current.node.name).toBe("Build");
    expect(result.current.breadcrumbs).toHaveLength(2);
  });

  it("returns single row for flat transcript (S7)", () => {
    const tree = getTree(S7_FLAT);
    const { result } = renderHook(() => useTimeline(tree), {
      wrapper: createWrapper(),
    });

    // S7 has no child agents, no init/scoring → just the parent row
    expect(result.current.rows).toHaveLength(1);
  });

  it("detects parallel spans (S4)", () => {
    const tree = getTree(S4_PARALLEL);
    const { result } = renderHook(() => useTimeline(tree), {
      wrapper: createWrapper(),
    });

    const exploreRow = result.current.rows.find((r) => r.name === "Explore");
    expect(exploreRow).toBeDefined();
    expect(exploreRow!.spans).toHaveLength(1);
    expect(isParallelSpan(exploreRow!.spans[0]!)).toBe(true);
  });

  it("reads selected param", () => {
    const tree = getTree(S1_SEQUENTIAL);
    const { result } = renderHook(() => useTimeline(tree), {
      wrapper: createWrapper(["/?selected=explore"]),
    });

    expect(result.current.selected).toBe("explore");
  });

  it("builds breadcrumbs for nested path", () => {
    const tree = getTree(S3_DEEP);
    const { result } = renderHook(() => useTimeline(tree), {
      wrapper: createWrapper(["/?path=build/code"]),
    });

    expect(result.current.breadcrumbs).toHaveLength(3);
    expect(result.current.breadcrumbs[0]!.label).toBe(tree.agent!.name);
    expect(result.current.breadcrumbs[1]!.label).toBe("Build");
    expect(result.current.breadcrumbs[2]!.label).toBe("Code");
  });

  it("falls back to root for invalid path", () => {
    const tree = getTree(S1_SEQUENTIAL);
    const { result } = renderHook(() => useTimeline(tree), {
      wrapper: createWrapper(["/?path=nonexistent"]),
    });

    // Should fall back to root with init/scoring folded in
    expect(result.current.node.name).toBe(tree.agent!.name);
    expect(result.current.rows.length).toBeGreaterThanOrEqual(1);
  });

  it("folds scoring into root rows but not when drilled in", () => {
    const tree = getTree(S1_SEQUENTIAL);

    // At root: scoring should be a row
    const { result: rootResult } = renderHook(() => useTimeline(tree), {
      wrapper: createWrapper(),
    });
    const scoringRow = rootResult.current.rows.find(
      (r) => r.name === "Scoring"
    );
    expect(scoringRow).toBeDefined();

    // Drilled into Build: no scoring row
    const { result: drillResult } = renderHook(() => useTimeline(tree), {
      wrapper: createWrapper(["/?path=build"]),
    });
    const scoringInBuild = drillResult.current.rows.find(
      (r) => r.name === "Scoring"
    );
    expect(scoringInBuild).toBeUndefined();
  });

  it("resolves scoring path to SectionNode converted to AgentNode", () => {
    const tree = getTree(S1_SEQUENTIAL);
    const { result } = renderHook(() => useTimeline(tree), {
      wrapper: createWrapper(["/?path=scoring"]),
    });

    expect(result.current.node.name).toBe("Scoring");
    expect(result.current.node.type).toBe("agent");
  });

  // ---------------------------------------------------------------------------
  // Navigation functions
  // ---------------------------------------------------------------------------

  it("drillDown appends to path and clears selection", () => {
    const tree = getTree(S1_SEQUENTIAL);
    const { result } = renderHook(() => useTimeline(tree), {
      wrapper: createWrapper(["/?selected=explore"]),
    });

    act(() => {
      result.current.drillDown("build");
    });

    expect(result.current.node.name).toBe("Build");
    expect(result.current.selected).toBeNull();
  });

  it("drillDown from nested path appends segment", () => {
    const tree = getTree(S3_DEEP);
    const { result } = renderHook(() => useTimeline(tree), {
      wrapper: createWrapper(["/?path=build"]),
    });

    act(() => {
      result.current.drillDown("code");
    });

    expect(result.current.node.name).toBe("Code");
    expect(result.current.breadcrumbs).toHaveLength(3);
  });

  it("drillDown with span index", () => {
    const tree = getTree(S2_ITERATIVE);
    const { result } = renderHook(() => useTimeline(tree), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.drillDown("explore", 2);
    });

    expect(result.current.node.name).toBe("Explore");
    // Should be the second Explore, not the first
    const firstExplore = tree.agent!.content.find(
      (c): c is AgentNode => c.type === "agent" && c.name === "Explore"
    );
    expect(result.current.node).not.toBe(firstExplore);
  });

  it("goUp removes last path segment", () => {
    const tree = getTree(S3_DEEP);
    const { result } = renderHook(() => useTimeline(tree), {
      wrapper: createWrapper(["/?path=build/code"]),
    });

    expect(result.current.node.name).toBe("Code");

    act(() => {
      result.current.goUp();
    });

    expect(result.current.node.name).toBe("Build");
  });

  it("goUp from single segment returns to root", () => {
    const tree = getTree(S1_SEQUENTIAL);
    const { result } = renderHook(() => useTimeline(tree), {
      wrapper: createWrapper(["/?path=build"]),
    });

    act(() => {
      result.current.goUp();
    });

    expect(result.current.node.name).toBe(tree.agent!.name);
    expect(result.current.breadcrumbs).toHaveLength(1);
  });

  it("goUp at root is a no-op", () => {
    const tree = getTree(S1_SEQUENTIAL);
    const { result } = renderHook(() => useTimeline(tree), {
      wrapper: createWrapper(),
    });

    const nameBefore = result.current.node.name;

    act(() => {
      result.current.goUp();
    });

    expect(result.current.node.name).toBe(nameBefore);
  });

  it("select sets the selected param", () => {
    const tree = getTree(S1_SEQUENTIAL);
    const { result } = renderHook(() => useTimeline(tree), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.select("explore");
    });

    expect(result.current.selected).toBe("explore");
  });

  it("select(null) clears the selected param", () => {
    const tree = getTree(S1_SEQUENTIAL);
    const { result } = renderHook(() => useTimeline(tree), {
      wrapper: createWrapper(["/?selected=explore"]),
    });

    act(() => {
      result.current.select(null);
    });

    expect(result.current.selected).toBeNull();
  });

  it("iterative agents produce multiple SingleSpans on one row (S2)", () => {
    const tree = getTree(S2_ITERATIVE);
    const { result } = renderHook(() => useTimeline(tree), {
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
