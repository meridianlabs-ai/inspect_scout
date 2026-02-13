import { describe, expect, it } from "vitest";

import type { AgentNode, SectionNode } from "../../components/transcript/nodes";

import {
  computeSwimLaneRows,
  isParallelSpan,
  isSingleSpan,
  sectionToAgent,
} from "./swimlaneRows";
import { timelineScenarios } from "./syntheticNodes";

// =============================================================================
// Test helpers
// =============================================================================

const BASE = new Date("2025-01-15T10:00:00Z").getTime();

function ts(offsetSeconds: number): Date {
  return new Date(BASE + offsetSeconds * 1000);
}

/** Minimal AgentNode builder for edge-case tests. */
function makeAgent(
  name: string,
  startSec: number,
  endSec: number,
  tokens: number,
  content: AgentNode["content"] = [],
  options?: { utility?: boolean }
): AgentNode {
  return {
    type: "agent",
    id: name.toLowerCase(),
    name,
    source: { source: "span", spanId: name.toLowerCase() },
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

function getScenarioAgent(index: number): AgentNode {
  const scenario = timelineScenarios[index];
  if (!scenario) throw new Error(`No scenario at index ${index}`);
  const node = scenario.nodes.agent;
  if (!node) throw new Error(`Scenario ${index} has no agent`);
  return node;
}

// =============================================================================
// sectionToAgent
// =============================================================================

describe("sectionToAgent", () => {
  it("converts a scoring SectionNode to an AgentNode", () => {
    const section: SectionNode = {
      type: "section",
      section: "scoring",
      content: [],
      startTime: ts(50),
      endTime: ts(55),
      totalTokens: 3200,
    };
    const result = sectionToAgent(section);

    expect(result.type).toBe("agent");
    expect(result.name).toBe("Scoring");
    expect(result.id).toBe("scoring");
    expect(result.utility).toBe(false);
    expect(result.branches).toEqual([]);
    expect(result.startTime).toEqual(ts(50));
    expect(result.endTime).toEqual(ts(55));
    expect(result.totalTokens).toBe(3200);
    expect(result.content).toBe(section.content);
  });

  it("converts an init SectionNode to an AgentNode", () => {
    const section: SectionNode = {
      type: "section",
      section: "init",
      content: [],
      startTime: ts(0),
      endTime: ts(2),
      totalTokens: 500,
    };
    const result = sectionToAgent(section);

    expect(result.name).toBe("Init");
    expect(result.id).toBe("init");
  });
});

// =============================================================================
// computeSwimLaneRows
// =============================================================================

describe("computeSwimLaneRows", () => {
  // ---------------------------------------------------------------------------
  // Sequential agents (S1)
  // ---------------------------------------------------------------------------
  describe("sequential agents (S1)", () => {
    it("produces parent + 3 child rows, all SingleSpan", () => {
      const node = getScenarioAgent(S1_SEQUENTIAL);
      const rows = computeSwimLaneRows(node);

      expect(rows).toHaveLength(4);

      const names = rows.map((r) => r.name);
      expect(names).toEqual(["Transcript", "Explore", "Plan", "Build"]);

      for (const row of rows) {
        expect(row.spans).toHaveLength(1);
        const span = row.spans[0]!;
        expect(isSingleSpan(span)).toBe(true);
      }
    });

    it("includes scoring when folded into content", () => {
      const scenario = timelineScenarios[S1_SEQUENTIAL]!;
      const node = getScenarioAgent(S1_SEQUENTIAL);
      const scoring = scenario.nodes.scoring;
      expect(scoring).not.toBeNull();

      const withScoring: AgentNode = {
        ...node,
        content: [...node.content, sectionToAgent(scoring!)],
      };
      const rows = computeSwimLaneRows(withScoring);

      expect(rows).toHaveLength(5);

      const lastRow = rows[4]!;
      expect(lastRow.name).toBe("Scoring");
      expect(isSingleSpan(lastRow.spans[0]!)).toBe(true);
    });
  });

  // ---------------------------------------------------------------------------
  // Flat transcript (S7)
  // ---------------------------------------------------------------------------
  describe("flat transcript (S7)", () => {
    it("produces only the parent row when there are no child agents", () => {
      const node = getScenarioAgent(S7_FLAT);
      const rows = computeSwimLaneRows(node);

      expect(rows).toHaveLength(1);
      expect(rows[0]!.name).toBe("Transcript");
    });
  });

  // ---------------------------------------------------------------------------
  // Iterative agents (S2)
  // ---------------------------------------------------------------------------
  describe("iterative agents (S2)", () => {
    it("groups same-name agents into multiple SingleSpans on one row", () => {
      const node = getScenarioAgent(S2_ITERATIVE);
      const rows = computeSwimLaneRows(node);

      expect(rows).toHaveLength(4);
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
      const node = getScenarioAgent(S2_ITERATIVE);
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
    it("groups overlapping same-name agents into a ParallelSpan", () => {
      const node = getScenarioAgent(S4_PARALLEL);
      const rows = computeSwimLaneRows(node);

      expect(rows).toHaveLength(4);

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
      const node = getScenarioAgent(S4_PARALLEL);
      const rows = computeSwimLaneRows(node);

      const exploreRow = rows[1]!;
      // explore1: 2-14, explore2: 3-16, explore3: 2-12
      expect(exploreRow.startTime).toEqual(ts(2));
      expect(exploreRow.endTime).toEqual(ts(16));
    });

    it("aggregates tokens across all parallel agents", () => {
      const node = getScenarioAgent(S4_PARALLEL);
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
    it("excludes utility agents from swimlane rows", () => {
      const node = getScenarioAgent(S10_UTILITY);
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
      const node = getScenarioAgent(S8_MANY);
      const rows = computeSwimLaneRows(node);

      expect(rows).toHaveLength(11);
      expect(rows[0]!.name).toBe("Transcript");
    });

    it("orders child rows by start time", () => {
      const node = getScenarioAgent(S8_MANY);
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
      const node = getScenarioAgent(S3_DEEP);
      const rows = computeSwimLaneRows(node);

      // S3 top level: Transcript → Build (only direct child)
      expect(rows.map((r) => r.name)).toEqual(["Transcript", "Build"]);

      // Drilling into Build should show its children
      const buildAgent = node.content.find(
        (c): c is AgentNode => c.type === "agent" && c.name === "Build"
      );
      expect(buildAgent).toBeDefined();
      const buildRows = computeSwimLaneRows(buildAgent!);
      expect(buildRows.map((r) => r.name)).toEqual([
        "Build",
        "Code",
        "Test",
        "Fix",
      ]);

      // Drilling into Test should show its children
      const testAgent = buildAgent!.content.find(
        (c): c is AgentNode => c.type === "agent" && c.name === "Test"
      );
      expect(testAgent).toBeDefined();
      const testRows = computeSwimLaneRows(testAgent!);
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
        const node = scenario.nodes.agent;
        if (!node) continue;
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
    it("groups agents with different casings into one row", () => {
      const parent = makeAgent("Transcript", 0, 50, 10000, [
        makeAgent("explore", 2, 10, 3000),
        makeAgent("Explore", 12, 20, 3000),
        makeAgent("EXPLORE", 22, 30, 3000),
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
    it("returns just the parent row when content has only EventNodes", () => {
      const parent = makeAgent("Transcript", 0, 50, 10000);
      const rows = computeSwimLaneRows(parent);

      expect(rows).toHaveLength(1);
      expect(rows[0]!.name).toBe("Transcript");
    });

    it("excludes all children if all are utility agents", () => {
      const parent = makeAgent("Transcript", 0, 50, 5000, [
        makeAgent("util1", 5, 10, 1000, [], { utility: true }),
        makeAgent("util2", 15, 20, 1000, [], { utility: true }),
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
      const span = { agent: makeAgent("Test", 0, 10, 100) };
      expect(isSingleSpan(span)).toBe(true);
      expect(isParallelSpan(span)).toBe(false);
    });

    it("isParallelSpan identifies ParallelSpan correctly", () => {
      const span = {
        agents: [makeAgent("A", 0, 10, 100), makeAgent("B", 2, 12, 100)],
      };
      expect(isParallelSpan(span)).toBe(true);
      expect(isSingleSpan(span)).toBe(false);
    });
  });
});
