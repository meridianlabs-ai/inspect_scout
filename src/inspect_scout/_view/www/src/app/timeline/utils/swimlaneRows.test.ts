import { describe, expect, it } from "vitest";

import type { TimelineSpan } from "../../../components/transcript/timeline";
import { timelineScenarios } from "../syntheticNodes";

import {
  computeSwimLaneRows,
  isParallelSpan,
  isSingleSpan,
} from "./swimlaneRows";

// =============================================================================
// Test helpers
// =============================================================================

const BASE = new Date("2025-01-15T10:00:00Z").getTime();

function ts(offsetSeconds: number): Date {
  return new Date(BASE + offsetSeconds * 1000);
}

/** Minimal TimelineSpan builder for edge-case tests. */
function makeSpan(
  name: string,
  startSec: number,
  endSec: number,
  tokens: number,
  content: TimelineSpan["content"] = [],
  options?: { utility?: boolean }
): TimelineSpan {
  return {
    type: "span",
    id: name.toLowerCase(),
    name,
    spanType: null,
    content,
    branches: [],
    utility: options?.utility ?? false,
    startTime: ts(startSec),
    endTime: ts(endSec),
    totalTokens: tokens,
  };
}

/** Scenario lookup by index (matches timelineScenarios order). */
const S1_SEQUENTIAL = 0;
const S2_ITERATIVE = 1;
const S3_DEEP = 2;
const S4_PARALLEL = 3;
// S5_MARKERS = 4 (not needed for swimlane tests)
const S7_FLAT = 5;
const S8_MANY = 6;
const S10_UTILITY = 7;

function getScenarioRoot(index: number): TimelineSpan {
  const scenario = timelineScenarios[index];
  if (!scenario) throw new Error(`No scenario at index ${index}`);
  return scenario.timeline.root;
}

// =============================================================================
// computeSwimLaneRows
// =============================================================================

describe("computeSwimLaneRows", () => {
  // ---------------------------------------------------------------------------
  // Sequential agents (S1)
  // ---------------------------------------------------------------------------
  describe("sequential agents (S1)", () => {
    it("produces parent + 4 child rows (including scoring), all SingleSpan", () => {
      const node = getScenarioRoot(S1_SEQUENTIAL);
      const rows = computeSwimLaneRows(node);

      expect(rows).toHaveLength(5);

      const names = rows.map((r) => r.name);
      expect(names).toEqual([
        "Transcript",
        "Explore",
        "Plan",
        "Build",
        "Scoring",
      ]);

      for (const row of rows) {
        expect(row.spans).toHaveLength(1);
        const span = row.spans[0]!;
        expect(isSingleSpan(span)).toBe(true);
      }
    });
  });

  // ---------------------------------------------------------------------------
  // Flat transcript (S7)
  // ---------------------------------------------------------------------------
  describe("flat transcript (S7)", () => {
    it("produces only the parent row when there are no child spans", () => {
      const node = getScenarioRoot(S7_FLAT);
      const rows = computeSwimLaneRows(node);

      expect(rows).toHaveLength(1);
      expect(rows[0]!.name).toBe("Transcript");
    });
  });

  // ---------------------------------------------------------------------------
  // Iterative agents (S2)
  // ---------------------------------------------------------------------------
  describe("iterative agents (S2)", () => {
    it("groups same-name spans into multiple SingleSpans on one row", () => {
      const node = getScenarioRoot(S2_ITERATIVE);
      const rows = computeSwimLaneRows(node);

      expect(rows).toHaveLength(5);
      expect(rows[0]!.name).toBe("Transcript");

      const exploreRow = rows[1]!;
      expect(exploreRow.name).toBe("Explore");
      expect(exploreRow.spans).toHaveLength(2);
      expect(isSingleSpan(exploreRow.spans[0]!)).toBe(true);
      expect(isSingleSpan(exploreRow.spans[1]!)).toBe(true);

      const planRow = rows[2]!;
      expect(planRow.name).toBe("Plan");
      expect(planRow.spans).toHaveLength(2);

      const buildRow = rows[3]!;
      expect(buildRow.name).toBe("Build");
      expect(buildRow.spans).toHaveLength(1);
    });

    it("aggregates tokens across all spans in a row", () => {
      const node = getScenarioRoot(S2_ITERATIVE);
      const rows = computeSwimLaneRows(node);

      const exploreRow = rows[1]!;
      // explore1 (7200) + explore2 (7300) = 14500
      expect(exploreRow.totalTokens).toBe(14500);
    });
  });

  // ---------------------------------------------------------------------------
  // Parallel agents (S4)
  // ---------------------------------------------------------------------------
  describe("parallel agents (S4)", () => {
    it("groups overlapping same-name spans into a ParallelSpan", () => {
      const node = getScenarioRoot(S4_PARALLEL);
      const rows = computeSwimLaneRows(node);

      expect(rows).toHaveLength(5);

      const exploreRow = rows[1]!;
      expect(exploreRow.name).toBe("Explore");
      expect(exploreRow.spans).toHaveLength(1);

      const span = exploreRow.spans[0]!;
      expect(isParallelSpan(span)).toBe(true);
      if (isParallelSpan(span)) {
        expect(span.agents).toHaveLength(3);
      }
    });

    it("computes time range from earliest start to latest end", () => {
      const node = getScenarioRoot(S4_PARALLEL);
      const rows = computeSwimLaneRows(node);

      const exploreRow = rows[1]!;
      // explore1: 2-14, explore2: 3-16, explore3: 2-12
      expect(exploreRow.startTime).toEqual(ts(2));
      expect(exploreRow.endTime).toEqual(ts(16));
    });

    it("aggregates tokens across all parallel spans", () => {
      const node = getScenarioRoot(S4_PARALLEL);
      const rows = computeSwimLaneRows(node);

      const exploreRow = rows[1]!;
      // 8100 + 9400 + 6800 = 24300
      expect(exploreRow.totalTokens).toBe(24300);
    });
  });

  // ---------------------------------------------------------------------------
  // Utility agents (S10)
  // ---------------------------------------------------------------------------
  describe("utility agents (S10)", () => {
    it("excludes utility spans from swimlane rows", () => {
      const node = getScenarioRoot(S10_UTILITY);
      const rows = computeSwimLaneRows(node);

      // Parent (Transcript) + Build only — 4 utility agents excluded
      expect(rows).toHaveLength(2);
      expect(rows[0]!.name).toBe("Transcript");
      expect(rows[1]!.name).toBe("Build");
    });
  });

  // ---------------------------------------------------------------------------
  // Many rows (S8)
  // ---------------------------------------------------------------------------
  describe("many rows (S8)", () => {
    it("produces parent + 10 child rows", () => {
      const node = getScenarioRoot(S8_MANY);
      const rows = computeSwimLaneRows(node);

      expect(rows).toHaveLength(11);
      expect(rows[0]!.name).toBe("Transcript");
    });

    it("orders child rows by start time", () => {
      const node = getScenarioRoot(S8_MANY);
      const rows = computeSwimLaneRows(node);

      for (let i = 2; i < rows.length; i++) {
        const current = rows[i]!;
        const previous = rows[i - 1]!;
        expect(current.startTime.getTime()).toBeGreaterThanOrEqual(
          previous.startTime.getTime()
        );
      }
    });
  });

  // ---------------------------------------------------------------------------
  // Deep nesting (S3) — only direct children shown
  // ---------------------------------------------------------------------------
  describe("deep nesting (S3)", () => {
    it("shows only direct children, not grandchildren", () => {
      const node = getScenarioRoot(S3_DEEP);
      const rows = computeSwimLaneRows(node);

      // S3 top level: Transcript → Explore + Build + Scoring
      expect(rows.map((r) => r.name)).toEqual([
        "Transcript",
        "Explore",
        "Build",
        "Scoring",
      ]);

      // Drilling into Build should show its children
      const buildSpan = node.content.find(
        (c): c is TimelineSpan => c.type === "span" && c.name === "Build"
      );
      expect(buildSpan).toBeDefined();
      const buildRows = computeSwimLaneRows(buildSpan!);
      expect(buildRows.map((r) => r.name)).toEqual([
        "Build",
        "Code",
        "Test",
        "Fix",
      ]);

      // Drilling into Test should show its children
      const testSpan = buildSpan!.content.find(
        (c): c is TimelineSpan => c.type === "span" && c.name === "Test"
      );
      expect(testSpan).toBeDefined();
      const testRows = computeSwimLaneRows(testSpan!);
      expect(testRows.map((r) => r.name)).toEqual([
        "Test",
        "Generate",
        "Run",
        "Evaluate",
      ]);
    });
  });

  // ---------------------------------------------------------------------------
  // Row ordering
  // ---------------------------------------------------------------------------
  describe("row ordering", () => {
    it("parent row is always first", () => {
      for (const scenario of timelineScenarios) {
        const node = scenario.timeline.root;
        const rows = computeSwimLaneRows(node);
        if (rows.length > 0) {
          expect(rows[0]!.name).toBe(node.name);
        }
      }
    });
  });

  // ---------------------------------------------------------------------------
  // Case-insensitive grouping
  // ---------------------------------------------------------------------------
  describe("case-insensitive grouping", () => {
    it("groups spans with different casings into one row", () => {
      const parent = makeSpan("Transcript", 0, 50, 10000, [
        makeSpan("explore", 2, 10, 3000),
        makeSpan("Explore", 12, 20, 3000),
        makeSpan("EXPLORE", 22, 30, 3000),
      ]);
      const rows = computeSwimLaneRows(parent);

      expect(rows).toHaveLength(2); // parent + one Explore row

      const exploreRow = rows[1]!;
      expect(exploreRow.name).toBe("explore"); // display name from first encountered
      expect(exploreRow.spans).toHaveLength(3); // 3 SingleSpans (non-overlapping)
    });
  });

  // ---------------------------------------------------------------------------
  // Edge cases
  // ---------------------------------------------------------------------------
  describe("edge cases", () => {
    it("returns just the parent row when content has only events", () => {
      const parent = makeSpan("Transcript", 0, 50, 10000);
      const rows = computeSwimLaneRows(parent);

      expect(rows).toHaveLength(1);
      expect(rows[0]!.name).toBe("Transcript");
    });

    it("excludes all children if all are utility spans", () => {
      const parent = makeSpan("Transcript", 0, 50, 5000, [
        makeSpan("util1", 5, 10, 1000, [], { utility: true }),
        makeSpan("util2", 15, 20, 1000, [], { utility: true }),
      ]);
      const rows = computeSwimLaneRows(parent);

      expect(rows).toHaveLength(1);
    });
  });

  // ---------------------------------------------------------------------------
  // Type guards
  // ---------------------------------------------------------------------------
  describe("type guards", () => {
    it("isSingleSpan identifies SingleSpan correctly", () => {
      const span = { agent: makeSpan("Test", 0, 10, 100) };
      expect(isSingleSpan(span)).toBe(true);
      expect(isParallelSpan(span)).toBe(false);
    });

    it("isParallelSpan identifies ParallelSpan correctly", () => {
      const span = {
        agents: [makeSpan("A", 0, 10, 100), makeSpan("B", 2, 12, 100)],
      };
      expect(isParallelSpan(span)).toBe(true);
      expect(isSingleSpan(span)).toBe(false);
    });
  });
});
