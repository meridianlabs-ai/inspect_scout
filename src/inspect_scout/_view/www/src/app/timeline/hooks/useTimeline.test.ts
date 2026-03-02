// @vitest-environment jsdom
import { act, renderHook } from "@testing-library/react";
import { type PropsWithChildren, createElement } from "react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import {
  S1_SEQUENTIAL,
  S2_ITERATIVE,
  S3_DEEP,
  S4_PARALLEL,
  S7_FLAT,
  getTimeline,
} from "../testHelpers";
import { isSingleSpan } from "../utils/swimlaneRows";

import { useTimeline } from "./useTimeline";

// =============================================================================
// useTimeline hook (flat expanded view)
// =============================================================================

function createWrapper(initialEntries: string[] = ["/"]) {
  return function Wrapper({ children }: PropsWithChildren) {
    return createElement(MemoryRouter, { initialEntries }, children);
  };
}

describe("useTimeline", () => {
  it("returns root node with all flat rows (S1)", () => {
    const timeline = getTimeline(S1_SEQUENTIAL);
    const { result } = renderHook(() => useTimeline(timeline), {
      wrapper: createWrapper(),
    });

    expect(result.current.node.name).toBe(timeline.root.name);
    // S1 has: Transcript + Explore + Plan + Build + Scoring = 5 rows
    expect(result.current.rows).toHaveLength(5);
    // Default selection is root key
    expect(result.current.selected).toBe(result.current.rows[0]!.key);
  });

  it("returns single row for flat transcript (S7)", () => {
    const timeline = getTimeline(S7_FLAT);
    const { result } = renderHook(() => useTimeline(timeline), {
      wrapper: createWrapper(),
    });

    expect(result.current.rows).toHaveLength(1);
    expect(result.current.selected).toBe(result.current.rows[0]!.key);
  });

  it("includes all descendants for deep nesting (S3)", () => {
    const timeline = getTimeline(S3_DEEP);
    const { result } = renderHook(() => useTimeline(timeline), {
      wrapper: createWrapper(),
    });

    // S3 has: Transcript, Explore, Build, Code, Test, Generate, Run, Evaluate, Fix, Scoring
    expect(result.current.rows).toHaveLength(10);

    // Verify depths increase properly
    const depths = result.current.rows.map((r) => r.depth);
    expect(depths[0]).toBe(0); // Transcript
    expect(depths).toEqual([0, 1, 1, 2, 2, 3, 3, 3, 2, 1]);
  });

  it("expands parallel agents into separate rows (S4)", () => {
    const timeline = getTimeline(S4_PARALLEL);
    const { result } = renderHook(() => useTimeline(timeline), {
      wrapper: createWrapper(),
    });

    // S4 has 3 parallel Explore agents → 3 separate "Explore N" rows
    const exploreRows = result.current.rows.filter((r) =>
      r.name.startsWith("Explore")
    );
    expect(exploreRows).toHaveLength(3);
    expect(exploreRows[0]!.name).toBe("Explore 1");
    expect(exploreRows[1]!.name).toBe("Explore 2");
    expect(exploreRows[2]!.name).toBe("Explore 3");

    // Each should be a SingleSpan
    for (const row of exploreRows) {
      expect(row.spans).toHaveLength(1);
      expect(isSingleSpan(row.spans[0]!)).toBe(true);
    }
  });

  it("expands iterative agents into separate rows (S2)", () => {
    const timeline = getTimeline(S2_ITERATIVE);
    const { result } = renderHook(() => useTimeline(timeline), {
      wrapper: createWrapper(),
    });

    const exploreRows = result.current.rows.filter((r) =>
      r.name.startsWith("Explore")
    );
    expect(exploreRows).toHaveLength(2);
    expect(exploreRows[0]!.name).toBe("Explore 1");
    expect(exploreRows[1]!.name).toBe("Explore 2");

    for (const row of exploreRows) {
      expect(row.spans).toHaveLength(1);
      expect(isSingleSpan(row.spans[0]!)).toBe(true);
    }
  });

  it("node is always the root", () => {
    const timeline = getTimeline(S3_DEEP);
    const { result } = renderHook(() => useTimeline(timeline), {
      wrapper: createWrapper(),
    });

    expect(result.current.node).toBe(timeline.root);
  });

  // ---------------------------------------------------------------------------
  // Selection
  // ---------------------------------------------------------------------------

  it("reads selected param from URL", () => {
    const timeline = getTimeline(S1_SEQUENTIAL);
    const { result } = renderHook(() => useTimeline(timeline), {
      wrapper: createWrapper(["/?selected=transcript/explore"]),
    });

    expect(result.current.selected).toBe("transcript/explore");
  });

  it("select sets the selected param", () => {
    const timeline = getTimeline(S1_SEQUENTIAL);
    const { result } = renderHook(() => useTimeline(timeline), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.select("transcript/explore");
    });

    expect(result.current.selected).toBe("transcript/explore");
  });

  it("select(null) clears the selected param and defaults to root", () => {
    const timeline = getTimeline(S1_SEQUENTIAL);
    const { result } = renderHook(() => useTimeline(timeline), {
      wrapper: createWrapper(["/?selected=transcript/explore"]),
    });

    act(() => {
      result.current.select(null);
    });

    // With no explicit selection, defaults to root row key
    expect(result.current.selected).toBe(result.current.rows[0]!.key);
  });

  it("clearSelection removes the selected param", () => {
    const timeline = getTimeline(S1_SEQUENTIAL);
    const { result } = renderHook(() => useTimeline(timeline), {
      wrapper: createWrapper(["/?selected=transcript/explore"]),
    });

    act(() => {
      result.current.clearSelection();
    });

    expect(result.current.selected).toBe(result.current.rows[0]!.key);
  });

  it("all rows have unique keys", () => {
    const timeline = getTimeline(S3_DEEP);
    const { result } = renderHook(() => useTimeline(timeline), {
      wrapper: createWrapper(),
    });

    const keys = result.current.rows.map((r) => r.key);
    const uniqueKeys = new Set(keys);
    expect(uniqueKeys.size).toBe(keys.length);
  });
});
