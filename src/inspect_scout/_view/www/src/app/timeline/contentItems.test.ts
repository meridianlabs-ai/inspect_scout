import { describe, expect, it } from "vitest";

import type {
  Branch,
  TimelineEvent,
  TimelineSpan,
} from "../../components/transcript/timeline";
import type { ModelEvent } from "../../types/api-types";

import { buildContentItems } from "./contentItems";
import { timelineScenarios } from "./syntheticNodes";

// =============================================================================
// Test helpers
// =============================================================================

const BASE = new Date("2025-01-15T10:00:00Z").getTime();

function ts(offsetSeconds: number): Date {
  return new Date(BASE + offsetSeconds * 1000);
}

/** Minimal TimelineEvent with a specific UUID. */
function makeEventNode(uuid: string | null, startSec: number): TimelineEvent {
  const event: ModelEvent = {
    event: "model",
    model: "test",
    input: [],
    tools: [],
    tool_choice: "auto",
    config: {} as ModelEvent["config"],
    output: {
      choices: [],
      completion: "",
      error: null,
      metadata: null,
      model: "test",
      time: 1,
      usage: {
        input_tokens: 50,
        output_tokens: 50,
        total_tokens: 100,
        input_tokens_cache_read: null,
        input_tokens_cache_write: null,
        reasoning_tokens: null,
        total_cost: null,
      },
    },
    timestamp: ts(startSec).toISOString(),
    working_start: startSec,
    working_time: 1,
    cache: null,
    call: null,
    completed: null,
    error: null,
    metadata: null,
    pending: null,
    retries: null,
    role: null,
    span_id: null,
    traceback: null,
    traceback_ansi: null,
    uuid,
  };
  return {
    type: "event",
    event,
    startTime: ts(startSec),
    endTime: ts(startSec + 1),
    totalTokens: 100,
  };
}

/** Minimal TimelineSpan builder. */
function makeSpan(
  name: string,
  startSec: number,
  endSec: number,
  content: TimelineSpan["content"] = [],
  options?: { branches?: Branch[]; utility?: boolean }
): TimelineSpan {
  return {
    type: "span",
    id: name.toLowerCase(),
    name,
    spanType: null,
    content,
    branches: options?.branches ?? [],
    utility: options?.utility ?? false,
    startTime: ts(startSec),
    endTime: ts(endSec),
    totalTokens: 1000,
  };
}

/** Minimal Branch builder. */
function makeBranch(forkedAt: string, startSec: number): Branch {
  return {
    type: "branch",
    forkedAt,
    content: [makeEventNode(null, startSec)],
    startTime: ts(startSec),
    endTime: ts(startSec + 5),
    totalTokens: 500,
  };
}

/** Scenario lookup by index. */
const S1_SEQUENTIAL = 0;
const S2_ITERATIVE = 1;
const S3_DEEP = 2;
const S4_PARALLEL = 3;
const S7_FLAT = 5;
const S10_UTILITY = 7;
const S11A_BRANCHES = 8;
const S11B_BRANCHES_MULTI = 9;

function getScenarioRoot(index: number): TimelineSpan {
  const scenario = timelineScenarios[index];
  if (!scenario) throw new Error(`No scenario at index ${index}`);
  return scenario.timeline.root;
}

// =============================================================================
// buildContentItems
// =============================================================================

describe("buildContentItems", () => {
  // ---------------------------------------------------------------------------
  // Sequential agents (S1)
  // ---------------------------------------------------------------------------
  describe("sequential agents (S1)", () => {
    it("produces a mix of event and agent_card items", () => {
      const node = getScenarioRoot(S1_SEQUENTIAL);
      const items = buildContentItems(node);

      // Transcript has: modelEvent, Explore, Plan, Build, modelEvent, Scoring
      expect(items.length).toBeGreaterThan(0);

      const types = items.map((i) => i.type);
      expect(types).toContain("event");
      expect(types).toContain("agent_card");
      expect(types).not.toContain("branch_card");
    });

    it("preserves content order", () => {
      const node = getScenarioRoot(S1_SEQUENTIAL);
      const items = buildContentItems(node);

      // Items should match content order: first item type matches first content type
      for (let i = 0; i < node.content.length; i++) {
        const contentItem = node.content[i]!;
        const item = items[i]!;
        if (contentItem.type === "event") {
          expect(item.type).toBe("event");
        } else {
          expect(item.type).toBe("agent_card");
        }
      }
    });
  });

  // ---------------------------------------------------------------------------
  // Flat transcript (S7)
  // ---------------------------------------------------------------------------
  describe("flat transcript (S7)", () => {
    it("produces all event items when no child spans exist", () => {
      const node = getScenarioRoot(S7_FLAT);
      const items = buildContentItems(node);

      expect(items.length).toBeGreaterThan(0);
      for (const item of items) {
        expect(item.type).toBe("event");
      }
    });
  });

  // ---------------------------------------------------------------------------
  // Parallel agents (S4)
  // ---------------------------------------------------------------------------
  describe("parallel agents (S4)", () => {
    it("has consecutive agent_cards for parallel Explore spans", () => {
      const node = getScenarioRoot(S4_PARALLEL);
      const items = buildContentItems(node);

      const agentCards = items.filter((i) => i.type === "agent_card");
      // S4 has: 3 Explore + Plan + Build + Scoring = 6 agent cards
      expect(agentCards.length).toBe(6);

      // The 3 Explore spans should be consecutive
      const exploreIndices = items
        .map((item, idx) => ({ item, idx }))
        .filter(
          ({ item }) =>
            item.type === "agent_card" && item.agentNode.name === "Explore"
        )
        .map(({ idx }) => idx);

      expect(exploreIndices).toHaveLength(3);
      // Check they're consecutive
      expect(exploreIndices[1]! - exploreIndices[0]!).toBe(1);
      expect(exploreIndices[2]! - exploreIndices[1]!).toBe(1);
    });
  });

  // ---------------------------------------------------------------------------
  // Iterative agents (S2)
  // ---------------------------------------------------------------------------
  describe("iterative agents (S2)", () => {
    it("includes all iterative span instances as separate cards", () => {
      const node = getScenarioRoot(S2_ITERATIVE);
      const items = buildContentItems(node);

      const agentNames = items
        .filter((i) => i.type === "agent_card")
        .map((i) => {
          if (i.type !== "agent_card") throw new Error("unreachable");
          return i.agentNode.name;
        });

      // S2: explore1, plan1, explore2, plan2, build, scoring
      expect(agentNames).toEqual([
        "Explore",
        "Plan",
        "Explore",
        "Plan",
        "Build",
        "Scoring",
      ]);
    });
  });

  // ---------------------------------------------------------------------------
  // Utility agents (S10)
  // ---------------------------------------------------------------------------
  describe("utility agents (S10)", () => {
    it("includes utility spans as agent_cards", () => {
      const node = getScenarioRoot(S10_UTILITY);

      // Utility spans are children of Build, not Transcript
      const buildSpan = node.content.find(
        (c): c is TimelineSpan => c.type === "span" && c.name === "Build"
      );
      expect(buildSpan).toBeDefined();

      const items = buildContentItems(buildSpan!);

      const agentCards = items.filter((i) => i.type === "agent_card");
      expect(agentCards.length).toBe(4); // 4 utility spans

      const utilityCards = agentCards.filter(
        (i) => i.type === "agent_card" && i.agentNode.utility
      );
      expect(utilityCards).toHaveLength(4);
    });
  });

  // ---------------------------------------------------------------------------
  // Deep nesting (S3)
  // ---------------------------------------------------------------------------
  describe("deep nesting (S3)", () => {
    it("shows Build's direct children as agent_cards", () => {
      const node = getScenarioRoot(S3_DEEP);

      // Drill into Build
      const buildSpan = node.content.find(
        (c): c is TimelineSpan => c.type === "span" && c.name === "Build"
      );
      expect(buildSpan).toBeDefined();

      const items = buildContentItems(buildSpan!);
      const agentNames = items
        .filter((i) => i.type === "agent_card")
        .map((i) => {
          if (i.type !== "agent_card") throw new Error("unreachable");
          return i.agentNode.name;
        });

      expect(agentNames).toEqual(["Code", "Test", "Fix"]);
    });
  });

  // ---------------------------------------------------------------------------
  // Branches — single fork (S11a)
  // ---------------------------------------------------------------------------
  describe("branches — single fork (S11a)", () => {
    it("appends branch_cards when forkedAt UUID is not found", () => {
      const node = getScenarioRoot(S11A_BRANCHES);

      // Drill into Build (which has the branches)
      const buildSpan = node.content.find(
        (c): c is TimelineSpan => c.type === "span" && c.name === "Build"
      );
      expect(buildSpan).toBeDefined();
      expect(buildSpan!.branches).toHaveLength(2);

      const items = buildContentItems(buildSpan!);
      const branchCards = items.filter((i) => i.type === "branch_card");

      // 2 branches, both with forkedAt that doesn't match any event UUID
      expect(branchCards).toHaveLength(2);

      // Branch cards should be at the end (unmatched UUID)
      const lastTwo = items.slice(-2);
      expect(lastTwo[0]!.type).toBe("branch_card");
      expect(lastTwo[1]!.type).toBe("branch_card");
    });
  });

  // ---------------------------------------------------------------------------
  // Branches — multiple forks (S11b)
  // ---------------------------------------------------------------------------
  describe("branches — multiple forks (S11b)", () => {
    it("appends all branch_cards when forkedAt UUIDs are not found", () => {
      const node = getScenarioRoot(S11B_BRANCHES_MULTI);

      const buildSpan = node.content.find(
        (c): c is TimelineSpan => c.type === "span" && c.name === "Build"
      );
      expect(buildSpan).toBeDefined();
      expect(buildSpan!.branches).toHaveLength(3);

      const items = buildContentItems(buildSpan!);
      const branchCards = items.filter((i) => i.type === "branch_card");

      expect(branchCards).toHaveLength(3);
    });
  });

  // ---------------------------------------------------------------------------
  // Branch insertion at matched UUID
  // ---------------------------------------------------------------------------
  describe("branch insertion at matched UUID", () => {
    it("inserts branch_card after the event with matching UUID", () => {
      const event1 = makeEventNode("evt-1", 0);
      const event2 = makeEventNode("evt-2", 5);
      const event3 = makeEventNode("evt-3", 10);
      const branch = makeBranch("evt-2", 5);

      const parent = makeSpan("Root", 0, 20, [event1, event2, event3], {
        branches: [branch],
      });

      const items = buildContentItems(parent);

      expect(items).toHaveLength(4); // 3 events + 1 branch card
      expect(items[0]!.type).toBe("event");
      expect(items[1]!.type).toBe("event"); // evt-2
      expect(items[2]!.type).toBe("branch_card"); // inserted after evt-2
      expect(items[3]!.type).toBe("event"); // evt-3
    });

    it("groups multiple branches at the same fork point", () => {
      const event1 = makeEventNode("evt-1", 0);
      const event2 = makeEventNode("evt-2", 5);
      const branch1 = makeBranch("evt-1", 2);
      const branch2 = makeBranch("evt-1", 3);

      const parent = makeSpan("Root", 0, 20, [event1, event2], {
        branches: [branch1, branch2],
      });

      const items = buildContentItems(parent);

      expect(items).toHaveLength(4); // 2 events + 2 branch cards
      expect(items[0]!.type).toBe("event"); // evt-1
      expect(items[1]!.type).toBe("branch_card"); // after evt-1
      expect(items[2]!.type).toBe("branch_card"); // after evt-1
      expect(items[3]!.type).toBe("event"); // evt-2
    });

    it("inserts branches at different fork points", () => {
      const event1 = makeEventNode("evt-1", 0);
      const event2 = makeEventNode("evt-2", 5);
      const event3 = makeEventNode("evt-3", 10);
      const branchA = makeBranch("evt-1", 2);
      const branchB = makeBranch("evt-3", 12);

      const parent = makeSpan("Root", 0, 20, [event1, event2, event3], {
        branches: [branchA, branchB],
      });

      const items = buildContentItems(parent);

      expect(items).toHaveLength(5); // 3 events + 2 branch cards
      expect(items[0]!.type).toBe("event"); // evt-1
      expect(items[1]!.type).toBe("branch_card"); // after evt-1
      expect(items[2]!.type).toBe("event"); // evt-2
      expect(items[3]!.type).toBe("event"); // evt-3
      expect(items[4]!.type).toBe("branch_card"); // after evt-3
    });

    it("handles mix of matched and unmatched branches", () => {
      const event1 = makeEventNode("evt-1", 0);
      const event2 = makeEventNode("evt-2", 5);
      const matchedBranch = makeBranch("evt-1", 2);
      const unmatchedBranch = makeBranch("nonexistent", 8);

      const parent = makeSpan("Root", 0, 20, [event1, event2], {
        branches: [matchedBranch, unmatchedBranch],
      });

      const items = buildContentItems(parent);

      expect(items).toHaveLength(4); // 2 events + 2 branch cards
      expect(items[0]!.type).toBe("event"); // evt-1
      expect(items[1]!.type).toBe("branch_card"); // matched, after evt-1
      expect(items[2]!.type).toBe("event"); // evt-2
      expect(items[3]!.type).toBe("branch_card"); // unmatched, appended
    });
  });

  // ---------------------------------------------------------------------------
  // Edge cases
  // ---------------------------------------------------------------------------
  describe("edge cases", () => {
    it("returns empty array for span with no content", () => {
      const parent = makeSpan("Empty", 0, 10);
      const items = buildContentItems(parent);

      expect(items).toHaveLength(0);
    });

    it("returns empty array for span with no content but has branches", () => {
      const branch = makeBranch("nonexistent", 5);
      const parent = makeSpan("Empty", 0, 10, [], { branches: [branch] });
      const items = buildContentItems(parent);

      // Branch appended since no content to match UUID against
      expect(items).toHaveLength(1);
      expect(items[0]!.type).toBe("branch_card");
    });

    it("handles agent_card items mixed with events for branch matching", () => {
      const event1 = makeEventNode("evt-1", 0);
      const childSpan = makeSpan("Child", 5, 10);
      const event2 = makeEventNode("evt-2", 10);
      const branch = makeBranch("evt-2", 12);

      const parent = makeSpan("Root", 0, 20, [event1, childSpan, event2], {
        branches: [branch],
      });

      const items = buildContentItems(parent);

      expect(items).toHaveLength(4); // event + agent_card + event + branch_card
      expect(items[0]!.type).toBe("event");
      expect(items[1]!.type).toBe("agent_card");
      expect(items[2]!.type).toBe("event");
      expect(items[3]!.type).toBe("branch_card");
    });
  });
});
