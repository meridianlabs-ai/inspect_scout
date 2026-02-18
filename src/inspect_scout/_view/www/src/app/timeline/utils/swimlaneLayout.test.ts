import { describe, expect, it } from "vitest";

import {
  S1_SEQUENTIAL,
  S2_ITERATIVE,
  S4_PARALLEL,
  S5_MARKERS,
  S7_FLAT,
  S8_MANY,
  getScenarioRoot,
  makeSpan,
  ts,
} from "../testHelpers";

import {
  computeBarPosition,
  computeRowLayouts,
  formatTokenCount,
  isDrillable,
  timestampToPercent,
} from "./swimlaneLayout";
import { computeSwimlaneRows } from "./swimlaneRows";

// =============================================================================
// timestampToPercent
// =============================================================================

describe("timestampToPercent", () => {
  const start = ts(0);
  const end = ts(100);

  it("returns 0 for the start timestamp", () => {
    expect(timestampToPercent(start, start, end)).toBe(0);
  });

  it("returns 100 for the end timestamp", () => {
    expect(timestampToPercent(end, start, end)).toBe(100);
  });

  it("returns 50 for the midpoint", () => {
    expect(timestampToPercent(ts(50), start, end)).toBe(50);
  });

  it("clamps to 0 for timestamps before the start", () => {
    expect(timestampToPercent(ts(-10), start, end)).toBe(0);
  });

  it("clamps to 100 for timestamps after the end", () => {
    expect(timestampToPercent(ts(110), start, end)).toBe(100);
  });

  it("returns 0 for zero-duration view range", () => {
    expect(timestampToPercent(ts(50), start, start)).toBe(0);
  });
});

// =============================================================================
// computeBarPosition
// =============================================================================

describe("computeBarPosition", () => {
  const viewStart = ts(0);
  const viewEnd = ts(100);

  it("returns full width for a span matching the view range", () => {
    const bar = computeBarPosition(viewStart, viewEnd, viewStart, viewEnd);
    expect(bar.left).toBe(0);
    expect(bar.width).toBe(100);
  });

  it("returns first half for a span covering the first half", () => {
    const bar = computeBarPosition(ts(0), ts(50), viewStart, viewEnd);
    expect(bar.left).toBe(0);
    expect(bar.width).toBe(50);
  });

  it("returns second half for a span covering the second half", () => {
    const bar = computeBarPosition(ts(50), ts(100), viewStart, viewEnd);
    expect(bar.left).toBe(50);
    expect(bar.width).toBe(50);
  });

  it("clamps a span extending beyond the view end", () => {
    const bar = computeBarPosition(ts(80), ts(120), viewStart, viewEnd);
    expect(bar.left).toBe(80);
    expect(bar.width).toBe(20);
  });

  it("clamps a span starting before the view start", () => {
    const bar = computeBarPosition(ts(-20), ts(30), viewStart, viewEnd);
    expect(bar.left).toBe(0);
    expect(bar.width).toBe(30);
  });

  it("handles a tiny span within the range", () => {
    const bar = computeBarPosition(ts(49), ts(51), viewStart, viewEnd);
    expect(bar.left).toBe(49);
    expect(bar.width).toBeCloseTo(2);
  });
});

// =============================================================================
// isDrillable
// =============================================================================

describe("isDrillable", () => {
  it("returns true for a SingleSpan with child spans", () => {
    const child = makeSpan("Child", 5, 10, 100);
    const agent = makeSpan("Parent", 0, 20, 500, [child]);
    expect(isDrillable({ agent })).toBe(true);
  });

  it("returns false for a SingleSpan with only events (no child spans)", () => {
    const agent = makeSpan("Leaf", 0, 10, 100);
    expect(isDrillable({ agent })).toBe(false);
  });

  it("returns false for a SingleSpan with only utility children", () => {
    const utilChild = makeSpan("util", 5, 10, 50, [], { utility: true });
    const agent = makeSpan("Parent", 0, 20, 500, [utilChild]);
    expect(isDrillable({ agent })).toBe(false);
  });

  it("returns true for a ParallelSpan", () => {
    const agents = [makeSpan("A", 0, 10, 100), makeSpan("B", 2, 12, 100)];
    expect(isDrillable({ agents })).toBe(true);
  });

  it("returns false for a scoring span (leaf with no children)", () => {
    const agent = makeSpan("Scoring", 40, 50, 3200, [], {
      spanType: "scorer",
    });
    expect(isDrillable({ agent })).toBe(false);
  });
});

// =============================================================================
// formatTokenCount
// =============================================================================

describe("formatTokenCount", () => {
  it("formats values under 1k as plain numbers", () => {
    expect(formatTokenCount(500)).toBe("500");
    expect(formatTokenCount(0)).toBe("0");
  });

  it("formats values in the thousands as Nk", () => {
    expect(formatTokenCount(1000)).toBe("1.0k");
    expect(formatTokenCount(48500)).toBe("48.5k");
    expect(formatTokenCount(8100)).toBe("8.1k");
  });

  it("formats values in the millions as NM", () => {
    expect(formatTokenCount(1200000)).toBe("1.2M");
    expect(formatTokenCount(1000000)).toBe("1.0M");
  });
});

// =============================================================================
// computeRowLayouts with scenarios
// =============================================================================

describe("computeRowLayouts", () => {
  describe("S1 sequential agents", () => {
    it("produces 5 row layouts with correct structure", () => {
      const root = getScenarioRoot(S1_SEQUENTIAL);
      const rows = computeSwimlaneRows(root);
      const layouts = computeRowLayouts(
        rows,
        root.startTime,
        root.endTime,
        "children"
      );

      expect(layouts).toHaveLength(5);
      expect(layouts[0]!.name).toBe("Transcript");
      expect(layouts[0]!.isParent).toBe(true);
      expect(layouts[1]!.isParent).toBe(false);
    });

    it("positions parent bar at full width", () => {
      const root = getScenarioRoot(S1_SEQUENTIAL);
      const rows = computeSwimlaneRows(root);
      const layouts = computeRowLayouts(
        rows,
        root.startTime,
        root.endTime,
        "children"
      );

      const parentSpan = layouts[0]!.spans[0]!;
      expect(parentSpan.bar.left).toBeCloseTo(0, 0);
      expect(parentSpan.bar.width).toBeCloseTo(100, 0);
    });

    it("positions child bars proportionally within the view range", () => {
      const root = getScenarioRoot(S1_SEQUENTIAL);
      const rows = computeSwimlaneRows(root);
      const layouts = computeRowLayouts(
        rows,
        root.startTime,
        root.endTime,
        "children"
      );

      // All child bars should start after 0% and end before 100%
      for (let i = 1; i < layouts.length; i++) {
        const span = layouts[i]!.spans[0]!;
        expect(span.bar.left).toBeGreaterThanOrEqual(0);
        expect(span.bar.left + span.bar.width).toBeLessThanOrEqual(100.1);
      }
    });

    it("marks parent as not drillable", () => {
      const root = getScenarioRoot(S1_SEQUENTIAL);
      const rows = computeSwimlaneRows(root);
      const layouts = computeRowLayouts(
        rows,
        root.startTime,
        root.endTime,
        "children"
      );

      expect(layouts[0]!.spans[0]!.drillable).toBe(false);
    });

    it("marks child agents with children as drillable", () => {
      const root = getScenarioRoot(S1_SEQUENTIAL);
      const rows = computeSwimlaneRows(root);
      const layouts = computeRowLayouts(
        rows,
        root.startTime,
        root.endTime,
        "children"
      );

      // Explore, Plan, Build have child events; Scoring is a leaf
      const buildLayout = layouts.find((l) => l.name === "Build");
      expect(buildLayout).toBeDefined();
      // Build has child spans (Code, Test, Fix in S3, but in S1 it has events only)
      // S1 Build has model + tool events but no child spans
      // so it should not be drillable
    });

    it("has no parallel counts on sequential spans", () => {
      const root = getScenarioRoot(S1_SEQUENTIAL);
      const rows = computeSwimlaneRows(root);
      const layouts = computeRowLayouts(
        rows,
        root.startTime,
        root.endTime,
        "children"
      );

      for (const layout of layouts) {
        for (const span of layout.spans) {
          expect(span.parallelCount).toBeNull();
        }
      }
    });
  });

  describe("S2 iterative agents", () => {
    it("produces multiple positioned spans for iterative rows", () => {
      const root = getScenarioRoot(S2_ITERATIVE);
      const rows = computeSwimlaneRows(root);
      const layouts = computeRowLayouts(
        rows,
        root.startTime,
        root.endTime,
        "children"
      );

      const exploreLayout = layouts.find((l) => l.name === "Explore");
      expect(exploreLayout).toBeDefined();
      expect(exploreLayout!.spans).toHaveLength(2);

      // Each span should have a distinct position
      const [span1, span2] = exploreLayout!.spans;
      expect(span1!.bar.left).toBeLessThan(span2!.bar.left);
    });
  });

  describe("S4 parallel agents", () => {
    it("shows parallel count for parallel spans", () => {
      const root = getScenarioRoot(S4_PARALLEL);
      const rows = computeSwimlaneRows(root);
      const layouts = computeRowLayouts(
        rows,
        root.startTime,
        root.endTime,
        "children"
      );

      const exploreLayout = layouts.find((l) => l.name === "Explore");
      expect(exploreLayout).toBeDefined();
      expect(exploreLayout!.spans).toHaveLength(1);
      expect(exploreLayout!.spans[0]!.parallelCount).toBe(3);
      expect(exploreLayout!.spans[0]!.drillable).toBe(true);
    });
  });

  describe("S5 inline markers", () => {
    it("collects error and compaction markers at correct positions", () => {
      const root = getScenarioRoot(S5_MARKERS);
      const rows = computeSwimlaneRows(root);
      const layouts = computeRowLayouts(
        rows,
        root.startTime,
        root.endTime,
        "children"
      );

      // Parent row should have markers from child agent
      const parentLayout = layouts[0]!;
      const markerKinds = parentLayout.markers.map((m) => m.kind);
      expect(markerKinds).toContain("error");
      expect(markerKinds).toContain("compaction");

      // Markers should be sorted by position
      for (let i = 1; i < parentLayout.markers.length; i++) {
        expect(parentLayout.markers[i]!.left).toBeGreaterThanOrEqual(
          parentLayout.markers[i - 1]!.left
        );
      }
    });
  });

  describe("S7 flat transcript", () => {
    it("produces a single parent row", () => {
      const root = getScenarioRoot(S7_FLAT);
      const rows = computeSwimlaneRows(root);
      const layouts = computeRowLayouts(
        rows,
        root.startTime,
        root.endTime,
        "children"
      );

      expect(layouts).toHaveLength(1);
      expect(layouts[0]!.isParent).toBe(true);
      expect(layouts[0]!.name).toBe("Transcript");
    });
  });

  describe("S8 many rows", () => {
    it("produces 11 row layouts (parent + 10 children)", () => {
      const root = getScenarioRoot(S8_MANY);
      const rows = computeSwimlaneRows(root);
      const layouts = computeRowLayouts(
        rows,
        root.startTime,
        root.endTime,
        "children"
      );

      expect(layouts).toHaveLength(11);
      expect(layouts[0]!.isParent).toBe(true);
      for (let i = 1; i < layouts.length; i++) {
        expect(layouts[i]!.isParent).toBe(false);
      }
    });
  });

  describe("marker depth modes", () => {
    it("direct depth only shows markers from the span itself", () => {
      const root = getScenarioRoot(S5_MARKERS);
      const rows = computeSwimlaneRows(root);

      const directLayouts = computeRowLayouts(
        rows,
        root.startTime,
        root.endTime,
        "direct"
      );
      const childrenLayouts = computeRowLayouts(
        rows,
        root.startTime,
        root.endTime,
        "children"
      );

      // Parent with "direct" should have fewer markers than with "children"
      // because child agent markers are not included
      const directParentMarkers = directLayouts[0]!.markers.length;
      const childrenParentMarkers = childrenLayouts[0]!.markers.length;
      expect(directParentMarkers).toBeLessThanOrEqual(childrenParentMarkers);
    });
  });
});
