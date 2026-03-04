import { describe, expect, it } from "vitest";

import type { TimelineSpan } from "../../../components/transcript/timeline";
import {
  S1_SEQUENTIAL,
  S2_ITERATIVE,
  S3_DEEP,
  S4_PARALLEL,
  S7_FLAT,
  S8_MANY,
  S10_UTILITY,
  getScenarioRoot,
  makeSpan,
  timelineScenarios,
  ts,
} from "../testHelpers";

import {
  assignToLanes,
  computeFlatSwimlaneRows,
  computeSwimlaneRows,
  isParallelSpan,
  isSingleSpan,
} from "./swimlaneRows";

// =============================================================================
// computeSwimlaneRows
// =============================================================================

describe("computeSwimlaneRows", () => {
  // ---------------------------------------------------------------------------
  // Sequential agents (S1)
  // ---------------------------------------------------------------------------
  describe("sequential agents (S1)", () => {
    it("produces parent + 4 child rows (including scoring), all SingleSpan", () => {
      const node = getScenarioRoot(S1_SEQUENTIAL);
      const rows = computeSwimlaneRows(node);

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
      const rows = computeSwimlaneRows(node);

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
      const rows = computeSwimlaneRows(node);

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
      const rows = computeSwimlaneRows(node);

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
      const rows = computeSwimlaneRows(node);

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
      const rows = computeSwimlaneRows(node);

      const exploreRow = rows[1]!;
      // explore1: 2-14, explore2: 3-16, explore3: 2-12
      expect(exploreRow.startTime).toEqual(ts(2));
      expect(exploreRow.endTime).toEqual(ts(16));
    });

    it("aggregates tokens across all parallel spans", () => {
      const node = getScenarioRoot(S4_PARALLEL);
      const rows = computeSwimlaneRows(node);

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
      const rows = computeSwimlaneRows(node);

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
      const rows = computeSwimlaneRows(node);

      expect(rows).toHaveLength(11);
      expect(rows[0]!.name).toBe("Transcript");
    });

    it("orders child rows by start time", () => {
      const node = getScenarioRoot(S8_MANY);
      const rows = computeSwimlaneRows(node);

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
      const rows = computeSwimlaneRows(node);

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
      const buildRows = computeSwimlaneRows(buildSpan!);
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
      const testRows = computeSwimlaneRows(testSpan!);
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
        const rows = computeSwimlaneRows(node);
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
      const rows = computeSwimlaneRows(parent);

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
      const rows = computeSwimlaneRows(parent);

      expect(rows).toHaveLength(1);
      expect(rows[0]!.name).toBe("Transcript");
    });

    it("excludes all children if all are utility spans", () => {
      const parent = makeSpan("Transcript", 0, 50, 5000, [
        makeSpan("util1", 5, 10, 1000, [], { utility: true }),
        makeSpan("util2", 15, 20, 1000, [], { utility: true }),
      ]);
      const rows = computeSwimlaneRows(parent);

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

// =============================================================================
// computeFlatSwimlaneRows
// =============================================================================

describe("computeFlatSwimlaneRows", () => {
  describe("sequential agents (S1)", () => {
    it("produces the same rows as computeSwimlaneRows for a flat tree", () => {
      const node = getScenarioRoot(S1_SEQUENTIAL);
      const rows = computeFlatSwimlaneRows(node);

      expect(rows).toHaveLength(5);
      expect(rows.map((r) => r.name)).toEqual([
        "Transcript",
        "Explore",
        "Plan",
        "Build",
        "Scoring",
      ]);
    });

    it("assigns correct depths (0 for root, 1 for children)", () => {
      const node = getScenarioRoot(S1_SEQUENTIAL);
      const rows = computeFlatSwimlaneRows(node);

      expect(rows.map((r) => r.depth)).toEqual([0, 1, 1, 1, 1]);
    });

    it("assigns unique keys encoding tree position", () => {
      const node = getScenarioRoot(S1_SEQUENTIAL);
      const rows = computeFlatSwimlaneRows(node);
      const keys = rows.map((r) => r.key);

      // All keys should be unique
      expect(new Set(keys).size).toBe(keys.length);
      // Root key
      expect(keys[0]).toBe("transcript");
      // Children have parent prefix
      expect(keys[1]).toBe("transcript/explore");
    });

    it("produces only SingleSpan rows (no ParallelSpan)", () => {
      const node = getScenarioRoot(S1_SEQUENTIAL);
      const rows = computeFlatSwimlaneRows(node);

      for (const row of rows) {
        expect(row.spans).toHaveLength(1);
        expect(isSingleSpan(row.spans[0]!)).toBe(true);
      }
    });
  });

  describe("flat transcript (S7)", () => {
    it("produces only the parent row", () => {
      const node = getScenarioRoot(S7_FLAT);
      const rows = computeFlatSwimlaneRows(node);

      expect(rows).toHaveLength(1);
      expect(rows[0]!.name).toBe("Transcript");
      expect(rows[0]!.depth).toBe(0);
    });
  });

  describe("deep nesting (S3)", () => {
    it("shows all descendants in depth-first pre-order", () => {
      const node = getScenarioRoot(S3_DEEP);
      const rows = computeFlatSwimlaneRows(node);

      // S3 tree:
      //   Transcript (0)
      //     Explore (1)
      //     Build (1)
      //       Code (2)
      //       Test (2)
      //         Generate (3)
      //         Run (3)
      //         Evaluate (3)
      //       Fix (2)
      //     Scoring (1)
      expect(rows.map((r) => r.name)).toEqual([
        "Transcript",
        "Explore",
        "Build",
        "Code",
        "Test",
        "Generate",
        "Run",
        "Evaluate",
        "Fix",
        "Scoring",
      ]);
    });

    it("assigns correct depths at each level", () => {
      const node = getScenarioRoot(S3_DEEP);
      const rows = computeFlatSwimlaneRows(node);

      expect(rows.map((r) => r.depth)).toEqual([
        0, // Transcript
        1, // Explore
        1, // Build
        2, // Code
        2, // Test
        3, // Generate
        3, // Run
        3, // Evaluate
        2, // Fix
        1, // Scoring
      ]);
    });

    it("assigns hierarchical keys", () => {
      const node = getScenarioRoot(S3_DEEP);
      const rows = computeFlatSwimlaneRows(node);

      expect(rows[0]!.key).toBe("transcript");
      expect(rows[2]!.key).toBe("transcript/build");
      expect(rows[3]!.key).toBe("transcript/build/code");
      expect(rows[4]!.key).toBe("transcript/build/test");
      expect(rows[5]!.key).toBe("transcript/build/test/generate");
    });
  });

  describe("parallel agents (S4)", () => {
    it("expands parallel agents into separate numbered rows", () => {
      const node = getScenarioRoot(S4_PARALLEL);
      const rows = computeFlatSwimlaneRows(node);

      // S4: Transcript, Explore 1, Explore 2, Explore 3, Plan, Build, Scoring
      const exploreRows = rows.filter((r) => r.name.startsWith("Explore"));
      expect(exploreRows).toHaveLength(3);
      expect(exploreRows.map((r) => r.name)).toEqual([
        "Explore 1",
        "Explore 2",
        "Explore 3",
      ]);

      // All at depth 1
      for (const row of exploreRows) {
        expect(row.depth).toBe(1);
      }

      // Each has a unique key
      const keys = new Set(exploreRows.map((r) => r.key));
      expect(keys.size).toBe(3);
    });

    it("each parallel row is a SingleSpan (not grouped)", () => {
      const node = getScenarioRoot(S4_PARALLEL);
      const rows = computeFlatSwimlaneRows(node);

      for (const row of rows) {
        expect(row.spans).toHaveLength(1);
        expect(isSingleSpan(row.spans[0]!)).toBe(true);
      }
    });
  });

  describe("iterative agents (S2)", () => {
    it("collapses iterative agents onto one row with multiple bars", () => {
      const node = getScenarioRoot(S2_ITERATIVE);
      const rows = computeFlatSwimlaneRows(node);

      const exploreRows = rows.filter((r) => r.name.startsWith("Explore"));
      expect(exploreRows).toHaveLength(1);
      expect(exploreRows[0]!.name).toBe("Explore");
      // Two non-overlapping spans → two SingleSpan bars
      expect(exploreRows[0]!.spans).toHaveLength(2);
      expect(isSingleSpan(exploreRows[0]!.spans[0]!)).toBe(true);
      expect(isSingleSpan(exploreRows[0]!.spans[1]!)).toBe(true);
    });

    it("aggregates token counts across iterative spans", () => {
      const node = getScenarioRoot(S2_ITERATIVE);
      const rows = computeFlatSwimlaneRows(node);

      const exploreRow = rows.find((r) => r.name === "Explore")!;
      // explore1 = 7200, explore2 = 7300
      expect(exploreRow.totalTokens).toBe(14500);
    });
  });

  describe("utility agents (S10)", () => {
    it("excludes utility spans", () => {
      const node = getScenarioRoot(S10_UTILITY);
      const rows = computeFlatSwimlaneRows(node);

      // Parent (Transcript) + Build only — 4 utility agents excluded
      expect(rows).toHaveLength(2);
      expect(rows[0]!.name).toBe("Transcript");
      expect(rows[1]!.name).toBe("Build");
    });
  });

  describe("row ordering", () => {
    it("parent row is always first with depth 0", () => {
      for (const scenario of timelineScenarios) {
        const node = scenario.timeline.root;
        const rows = computeFlatSwimlaneRows(node);
        expect(rows[0]!.name).toBe(node.name);
        expect(rows[0]!.depth).toBe(0);
      }
    });
  });

  describe("edge cases", () => {
    it("collapses non-overlapping same-name agents onto one row", () => {
      const parent = makeSpan("Root", 0, 50, 10000, [
        makeSpan("explore", 2, 10, 3000),
        makeSpan("Explore", 12, 20, 3000),
        makeSpan("EXPLORE", 22, 30, 3000),
      ]);
      const rows = computeFlatSwimlaneRows(parent);

      // 3 same-name (case-insensitive), non-overlapping → one row with 3 bars
      expect(rows).toHaveLength(2); // parent + 1 explore
      expect(rows[1]!.name).toBe("explore");
      expect(rows[1]!.spans).toHaveLength(3);
    });

    it("single child uses unnumbered name", () => {
      const parent = makeSpan("Root", 0, 50, 10000, [
        makeSpan("Build", 5, 40, 8000),
      ]);
      const rows = computeFlatSwimlaneRows(parent);

      expect(rows).toHaveLength(2);
      expect(rows[1]!.name).toBe("Build"); // no number suffix
    });
  });

  // ---------------------------------------------------------------------------
  // Lane reuse (mixed parallel + sequential)
  // ---------------------------------------------------------------------------
  describe("lane reuse", () => {
    it("packs non-overlapping spans into minimum lanes", () => {
      // 5 Explore spans, max 2 concurrent at any time
      // E1: 0-10, E2: 5-15 (overlap), E3: 20-30, E4: 25-35 (overlap), E5: 40-50
      // Lane 1: E1, E3, E5 | Lane 2: E2, E4
      const parent = makeSpan("Root", 0, 60, 50000, [
        makeSpan("Explore", 0, 10, 3000),
        makeSpan("Explore", 5, 15, 4000),
        makeSpan("Explore", 20, 30, 5000),
        makeSpan("Explore", 25, 35, 6000),
        makeSpan("Explore", 40, 50, 7000),
      ]);
      const rows = computeFlatSwimlaneRows(parent);

      // Parent + 2 lanes
      expect(rows).toHaveLength(3);
      expect(rows[0]!.name).toBe("Root");

      const exploreRows = rows.filter((r) => r.name.startsWith("Explore"));
      expect(exploreRows).toHaveLength(2);
      expect(exploreRows[0]!.name).toBe("Explore 1");
      expect(exploreRows[1]!.name).toBe("Explore 2");

      // Lane 1: 3 bars (E1, E3, E5)
      expect(exploreRows[0]!.spans).toHaveLength(3);
      // Lane 2: 2 bars (E2, E4)
      expect(exploreRows[1]!.spans).toHaveLength(2);
    });

    it("assigns unique hierarchical keys to lanes", () => {
      const parent = makeSpan("Root", 0, 40, 20000, [
        makeSpan("Explore", 0, 10, 3000),
        makeSpan("Explore", 5, 15, 4000),
        makeSpan("Explore", 20, 30, 5000),
      ]);
      const rows = computeFlatSwimlaneRows(parent);

      expect(rows[1]!.key).toBe("root/explore-1");
      expect(rows[2]!.key).toBe("root/explore-2");
    });

    it("aggregates tokens per lane", () => {
      const parent = makeSpan("Root", 0, 60, 50000, [
        makeSpan("Explore", 0, 10, 3000),
        makeSpan("Explore", 5, 15, 4000),
        makeSpan("Explore", 20, 30, 5000),
      ]);
      const rows = computeFlatSwimlaneRows(parent);

      const exploreRows = rows.filter((r) => r.name.startsWith("Explore"));
      // Lane 1: 3000 + 5000 = 8000
      expect(exploreRows[0]!.totalTokens).toBe(8000);
      // Lane 2: 4000
      expect(exploreRows[1]!.totalTokens).toBe(4000);
    });

    it("computes correct time range per lane", () => {
      const parent = makeSpan("Root", 0, 60, 50000, [
        makeSpan("Explore", 0, 10, 3000),
        makeSpan("Explore", 5, 15, 4000),
        makeSpan("Explore", 20, 30, 5000),
      ]);
      const rows = computeFlatSwimlaneRows(parent);

      const exploreRows = rows.filter((r) => r.name.startsWith("Explore"));
      // Lane 1: E1(0-10) + E3(20-30) → start=0, end=30
      expect(exploreRows[0]!.startTime).toEqual(ts(0));
      expect(exploreRows[0]!.endTime).toEqual(ts(30));
      // Lane 2: E2(5-15) → start=5, end=15
      expect(exploreRows[1]!.startTime).toEqual(ts(5));
      expect(exploreRows[1]!.endTime).toEqual(ts(15));
    });

    it("merges children from multiple spans in the same lane", () => {
      const parent = makeSpan("Root", 0, 60, 50000, [
        makeSpan("Explore", 0, 10, 3000, [
          makeSpan("Search", 2, 8, 1500),
        ]),
        makeSpan("Explore", 5, 15, 4000, [
          makeSpan("Analyze", 7, 13, 2000),
        ]),
        makeSpan("Explore", 20, 30, 5000, [
          makeSpan("Search", 22, 28, 2500),
        ]),
      ]);
      const rows = computeFlatSwimlaneRows(parent);

      // Lane 1: E1(0-10) + E3(20-30) → children: Search(2-8), Search(22-28)
      // Lane 2: E2(5-15) → children: Analyze(7-13)
      const searchRows = rows.filter((r) => r.name === "Search");
      expect(searchRows).toHaveLength(1);
      expect(searchRows[0]!.spans).toHaveLength(2); // two bars
      expect(searchRows[0]!.depth).toBe(2);

      const analyzeRows = rows.filter((r) => r.name === "Analyze");
      expect(analyzeRows).toHaveLength(1);
      expect(analyzeRows[0]!.depth).toBe(2);
    });

    it("all spans are SingleSpan (not grouped as ParallelSpan)", () => {
      const parent = makeSpan("Root", 0, 60, 50000, [
        makeSpan("Explore", 0, 10, 3000),
        makeSpan("Explore", 5, 15, 4000),
        makeSpan("Explore", 20, 30, 5000),
      ]);
      const rows = computeFlatSwimlaneRows(parent);

      for (const row of rows) {
        for (const span of row.spans) {
          expect(isSingleSpan(span)).toBe(true);
        }
      }
    });
  });
});

// =============================================================================
// assignToLanes
// =============================================================================

describe("assignToLanes", () => {
  it("returns empty array for empty input", () => {
    expect(assignToLanes([])).toEqual([]);
  });

  it("puts all non-overlapping spans in one lane", () => {
    const spans = [
      makeSpan("A", 0, 10, 100),
      makeSpan("B", 20, 30, 100),
      makeSpan("C", 40, 50, 100),
    ];
    const lanes = assignToLanes(spans);

    expect(lanes).toHaveLength(1);
    expect(lanes[0]).toHaveLength(3);
  });

  it("puts all overlapping spans in separate lanes", () => {
    const spans = [
      makeSpan("A", 0, 10, 100),
      makeSpan("B", 2, 12, 100),
      makeSpan("C", 4, 14, 100),
    ];
    const lanes = assignToLanes(spans);

    expect(lanes).toHaveLength(3);
    expect(lanes[0]).toHaveLength(1);
    expect(lanes[1]).toHaveLength(1);
    expect(lanes[2]).toHaveLength(1);
  });

  it("reuses lanes when spans become available", () => {
    // A: 0-10, B: 5-15, C: 20-30, D: 25-35, E: 40-50
    // Lane 1: A, C, E | Lane 2: B, D
    const spans = [
      makeSpan("A", 0, 10, 100),
      makeSpan("B", 5, 15, 100),
      makeSpan("C", 20, 30, 100),
      makeSpan("D", 25, 35, 100),
      makeSpan("E", 40, 50, 100),
    ];
    const lanes = assignToLanes(spans);

    expect(lanes).toHaveLength(2);
    expect(lanes[0]).toHaveLength(3); // A, C, E
    expect(lanes[1]).toHaveLength(2); // B, D
  });
});
