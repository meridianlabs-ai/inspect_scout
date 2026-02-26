import { describe, expect, it } from "vitest";

import type {
  TimelineBranch,
  TimelineEvent,
  TimelineSpan,
} from "../../../components/transcript/timeline";
import type {
  CompactionEvent,
  ModelEvent,
  ToolEvent,
} from "../../../types/api-types";
import {
  S11A_BRANCHES,
  S5_MARKERS,
  S7_FLAT,
  getScenarioRoot,
  makeSpan,
  ts,
} from "../testHelpers";

import { collectMarkers, isCompactionEvent, isErrorEvent } from "./markers";

// =============================================================================
// Test helpers
// =============================================================================

const NULL_CONFIG = {} as ModelEvent["config"];

function makeModelEventNode(
  startSec: number,
  options?: { error?: string; outputError?: string; uuid?: string }
): TimelineEvent {
  const event: ModelEvent = {
    event: "model",
    model: "test",
    input: [],
    tools: [],
    tool_choice: "auto",
    config: NULL_CONFIG,
    output: {
      choices: [],
      completion: "",
      error: options?.outputError ?? null,
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
    error: options?.error ?? null,
    metadata: null,
    pending: null,
    retries: null,
    role: null,
    span_id: null,
    traceback: null,
    traceback_ansi: null,
    uuid: options?.uuid ?? null,
  };
  return {
    type: "event",
    event,
    startTime: ts(startSec),
    endTime: ts(startSec + 1),
    totalTokens: 100,
    idleTime: 0,
  };
}

function makeToolEventNode(
  startSec: number,
  options?: {
    error?: { message: string; type: string };
    uuid?: string;
  }
): TimelineEvent {
  const event: ToolEvent = {
    event: "tool",
    type: "function",
    function: "test_tool",
    id: `call-${startSec}`,
    arguments: {},
    result: "ok",
    events: [],
    timestamp: ts(startSec).toISOString(),
    working_start: startSec,
    working_time: 1,
    error: options?.error
      ? {
          message: options.error.message,
          type: options.error.type as ToolEvent["error"] extends {
            type: infer T;
          } | null
            ? T
            : never,
        }
      : null,
    failed: options?.error ? true : null,
    agent: null,
    completed: null,
    message_id: null,
    metadata: null,
    pending: null,
    span_id: null,
    truncated: null,
    uuid: options?.uuid ?? null,
    view: null,
  };
  return {
    type: "event",
    event,
    startTime: ts(startSec),
    endTime: ts(startSec + 1),
    totalTokens: 0,
    idleTime: 0,
  };
}

function makeCompactionEventNode(
  startSec: number,
  options?: { uuid?: string }
): TimelineEvent {
  const event: CompactionEvent = {
    event: "compaction",
    type: "summary",
    tokens_before: 10000,
    tokens_after: 5000,
    timestamp: ts(startSec).toISOString(),
    working_start: startSec,
    metadata: null,
    pending: null,
    source: null,
    span_id: null,
    uuid: options?.uuid ?? null,
  };
  return {
    type: "event",
    event,
    startTime: ts(startSec),
    endTime: ts(startSec + 1),
    totalTokens: 0,
    idleTime: 0,
  };
}

// =============================================================================
// isErrorEvent
// =============================================================================

describe("isErrorEvent", () => {
  it("returns true for ToolEvent with error", () => {
    const node = makeToolEventNode(0, {
      error: { message: "fail", type: "timeout" },
    });
    expect(isErrorEvent(node.event)).toBe(true);
  });

  it("returns false for ToolEvent without error", () => {
    const node = makeToolEventNode(0);
    expect(isErrorEvent(node.event)).toBe(false);
  });

  it("returns true for ModelEvent with event.error", () => {
    const node = makeModelEventNode(0, { error: "Rate limit exceeded" });
    expect(isErrorEvent(node.event)).toBe(true);
  });

  it("returns true for ModelEvent with output.error", () => {
    const node = makeModelEventNode(0, { outputError: "API error" });
    expect(isErrorEvent(node.event)).toBe(true);
  });

  it("returns false for ModelEvent without error", () => {
    const node = makeModelEventNode(0);
    expect(isErrorEvent(node.event)).toBe(false);
  });

  it("returns false for CompactionEvent", () => {
    const node = makeCompactionEventNode(0);
    expect(isErrorEvent(node.event)).toBe(false);
  });
});

// =============================================================================
// isCompactionEvent
// =============================================================================

describe("isCompactionEvent", () => {
  it("returns true for CompactionEvent", () => {
    const node = makeCompactionEventNode(0);
    expect(isCompactionEvent(node.event)).toBe(true);
  });

  it("returns false for ModelEvent", () => {
    const node = makeModelEventNode(0);
    expect(isCompactionEvent(node.event)).toBe(false);
  });

  it("returns false for ToolEvent", () => {
    const node = makeToolEventNode(0);
    expect(isCompactionEvent(node.event)).toBe(false);
  });
});

// =============================================================================
// collectMarkers
// =============================================================================

describe("collectMarkers", () => {
  // ---------------------------------------------------------------------------
  // S5 (inline markers)
  // ---------------------------------------------------------------------------
  describe("S5 inline markers", () => {
    it("collects error and compaction markers from child span", () => {
      const transcript = getScenarioRoot(S5_MARKERS);

      // The markers are in the Agent child, not in Transcript directly
      const agent = transcript.content.find(
        (c): c is TimelineSpan => c.type === "span" && c.name === "Agent"
      );
      expect(agent).toBeDefined();

      const markers = collectMarkers(agent!, "direct");

      // S5 Agent has: 1 model error (sec 20), 1 tool error (sec 31), 1 compaction (sec 39)
      const errors = markers.filter((m) => m.kind === "error");
      const compactions = markers.filter((m) => m.kind === "compaction");

      expect(errors).toHaveLength(2);
      expect(compactions).toHaveLength(1);
    });

    it("collects markers from children when depth=children", () => {
      const transcript = getScenarioRoot(S5_MARKERS);

      // Transcript → Agent; depth=children should find Agent's markers
      const markers = collectMarkers(transcript, "children");

      const errors = markers.filter((m) => m.kind === "error");
      const compactions = markers.filter((m) => m.kind === "compaction");

      expect(errors).toHaveLength(2);
      expect(compactions).toHaveLength(1);
    });
  });

  // ---------------------------------------------------------------------------
  // S7 (flat, no errors)
  // ---------------------------------------------------------------------------
  describe("S7 flat transcript", () => {
    it("returns empty markers when no errors or compactions", () => {
      const node = getScenarioRoot(S7_FLAT);
      const markers = collectMarkers(node, "direct");

      expect(markers).toHaveLength(0);
    });
  });

  // ---------------------------------------------------------------------------
  // Depth modes
  // ---------------------------------------------------------------------------
  describe("depth modes", () => {
    it("direct: collects only from own events", () => {
      const childSpan = makeSpan("Child", 10, 20, 1000, [
        makeToolEventNode(12, {
          error: { message: "child error", type: "runtime" },
        }),
      ]);
      const parent = makeSpan("Parent", 0, 30, 1000, [
        makeModelEventNode(2, { error: "parent error" }),
        childSpan,
      ]);

      const markers = collectMarkers(parent, "direct");

      expect(markers).toHaveLength(1);
      expect(markers[0]!.kind).toBe("error");
      expect(markers[0]!.timestamp).toEqual(ts(2));
    });

    it("children: collects from own events + direct child spans", () => {
      const grandchild = makeSpan("Grandchild", 15, 18, 1000, [
        makeCompactionEventNode(16),
      ]);
      const child = makeSpan("Child", 10, 20, 1000, [
        makeToolEventNode(12, {
          error: { message: "child error", type: "runtime" },
        }),
        grandchild,
      ]);
      const parent = makeSpan("Parent", 0, 30, 1000, [
        makeModelEventNode(2, { error: "parent error" }),
        child,
      ]);

      const markers = collectMarkers(parent, "children");

      // parent error + child error = 2 (grandchild compaction not included)
      expect(markers).toHaveLength(2);
      expect(markers.map((m) => m.kind)).toEqual(["error", "error"]);
    });

    it("recursive: collects from the full subtree", () => {
      const grandchild = makeSpan("Grandchild", 15, 18, 1000, [
        makeCompactionEventNode(16),
      ]);
      const child = makeSpan("Child", 10, 20, 1000, [
        makeToolEventNode(12, {
          error: { message: "child error", type: "runtime" },
        }),
        grandchild,
      ]);
      const parent = makeSpan("Parent", 0, 30, 1000, [
        makeModelEventNode(2, { error: "parent error" }),
        child,
      ]);

      const markers = collectMarkers(parent, "recursive");

      // parent error + child error + grandchild compaction = 3
      expect(markers).toHaveLength(3);
      expect(markers.map((m) => m.kind)).toEqual([
        "error",
        "error",
        "compaction",
      ]);
    });
  });

  // ---------------------------------------------------------------------------
  // Branch markers
  // ---------------------------------------------------------------------------
  describe("branch markers", () => {
    it("creates branch markers when forkedAt matches an event UUID", () => {
      const event1 = makeModelEventNode(0, { uuid: "evt-1" });
      const event2 = makeModelEventNode(5, { uuid: "evt-2" });
      const branch: TimelineBranch = {
        type: "branch",
        forkedAt: "evt-1",
        content: [makeModelEventNode(2)],
        startTime: ts(2),
        endTime: ts(4),
        totalTokens: 100,
        idleTime: 0,
      };

      const parent = makeSpan("Root", 0, 20, 1000, [event1, event2], {
        branches: [branch],
      });

      const markers = collectMarkers(parent, "direct");

      expect(markers).toHaveLength(1);
      expect(markers[0]!.kind).toBe("branch");
      expect(markers[0]!.timestamp).toEqual(ts(0)); // evt-1's timestamp
      expect(markers[0]!.reference).toBe("evt-1");
    });

    it("silently drops branch markers when forkedAt UUID is not found", () => {
      const branch: TimelineBranch = {
        type: "branch",
        forkedAt: "nonexistent",
        content: [makeModelEventNode(2)],
        startTime: ts(2),
        endTime: ts(4),
        totalTokens: 100,
        idleTime: 0,
      };

      const parent = makeSpan("Root", 0, 20, 1000, [makeModelEventNode(0)], {
        branches: [branch],
      });

      const markers = collectMarkers(parent, "direct");

      expect(markers).toHaveLength(0);
    });

    it("silently drops branch markers with empty forkedAt", () => {
      const branch: TimelineBranch = {
        type: "branch",
        forkedAt: "",
        content: [makeModelEventNode(2)],
        startTime: ts(2),
        endTime: ts(4),
        totalTokens: 100,
        idleTime: 0,
      };

      const parent = makeSpan("Root", 0, 20, 1000, [makeModelEventNode(0)], {
        branches: [branch],
      });

      const markers = collectMarkers(parent, "direct");

      expect(markers).toHaveLength(0);
    });

    it("S11a: resolves branch markers from fork-point UUID", () => {
      const transcript = getScenarioRoot(S11A_BRANCHES);
      const buildSpan = transcript.content.find(
        (c): c is TimelineSpan => c.type === "span" && c.name === "Build"
      );
      expect(buildSpan).toBeDefined();
      expect(buildSpan!.branches).toHaveLength(2);

      const markers = collectMarkers(buildSpan!, "direct");

      // Both branches share forkedAt "model-call-5" → grouped into 1 marker
      const branchMarkers = markers.filter((m) => m.kind === "branch");
      expect(branchMarkers).toHaveLength(1);
      expect(branchMarkers[0]!.reference).toBe("model-call-5");
      expect(branchMarkers[0]!.tooltip).toContain("2 branches");
    });
  });

  // ---------------------------------------------------------------------------
  // Sort order
  // ---------------------------------------------------------------------------
  describe("sort order", () => {
    it("sorts markers by timestamp", () => {
      const parent = makeSpan("Root", 0, 30, 1000, [
        makeCompactionEventNode(20),
        makeToolEventNode(5, {
          error: { message: "early error", type: "runtime" },
        }),
        makeModelEventNode(10, { error: "mid error" }),
      ]);

      const markers = collectMarkers(parent, "direct");

      expect(markers).toHaveLength(3);
      expect(markers[0]!.timestamp).toEqual(ts(5));
      expect(markers[1]!.timestamp).toEqual(ts(10));
      expect(markers[2]!.timestamp).toEqual(ts(20));
    });

    it("sorts mixed error, compaction, and branch markers", () => {
      const event1 = makeModelEventNode(5, { uuid: "evt-fork" });
      const event2 = makeToolEventNode(15, {
        error: { message: "err", type: "runtime" },
      });
      const event3 = makeCompactionEventNode(25);

      const branch: TimelineBranch = {
        type: "branch",
        forkedAt: "evt-fork",
        content: [makeModelEventNode(6)],
        startTime: ts(6),
        endTime: ts(8),
        totalTokens: 100,
        idleTime: 0,
      };

      const parent = makeSpan("Root", 0, 30, 1000, [event1, event2, event3], {
        branches: [branch],
      });

      const markers = collectMarkers(parent, "direct");

      expect(markers).toHaveLength(3);
      expect(markers[0]!.kind).toBe("branch"); // ts(5)
      expect(markers[1]!.kind).toBe("error"); // ts(15)
      expect(markers[2]!.kind).toBe("compaction"); // ts(25)
    });
  });

  // ---------------------------------------------------------------------------
  // Edge cases
  // ---------------------------------------------------------------------------
  describe("edge cases", () => {
    it("returns empty array for span with no events", () => {
      const parent = makeSpan("Empty", 0, 10, 1000);
      const markers = collectMarkers(parent, "direct");

      expect(markers).toHaveLength(0);
    });

    it("returns empty array for span with only normal events", () => {
      const parent = makeSpan("Normal", 0, 10, 1000, [
        makeModelEventNode(2),
        makeToolEventNode(5),
      ]);
      const markers = collectMarkers(parent, "direct");

      expect(markers).toHaveLength(0);
    });
  });
});
