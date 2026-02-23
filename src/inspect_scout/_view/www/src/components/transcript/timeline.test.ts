/**
 * Tests for transcript nodes module.
 *
 * Uses the same JSON fixtures as the Python tests to ensure cross-language consistency.
 */

import { readdirSync, readFileSync } from "fs";
import { join } from "path";

import { describe, expect, it } from "vitest";

import type { Event } from "../../types/api-types";

import {
  TimelineBranch,
  type Timeline,
  TimelineEvent,
  TimelineSpan,
  buildTimeline,
} from "./timeline";

// =============================================================================
// Fixture Types
// =============================================================================

interface JsonEvent {
  event: string;
  uuid?: string;
  id?: string;
  name?: string;
  type?: string;
  parent_id?: string | null;
  span_id?: string | null;
  timestamp?: string;
  completed?: string;
  model?: string;
  function?: string;
  agent?: string;
  source?: string;
  input?: Array<{ role: string; content: string; tool_call_id?: string }>;
  output?: {
    usage?: {
      input_tokens?: number;
      output_tokens?: number;
    };
    choices?: Array<{
      message: { role: string; content: string };
      stop_reason?: string;
    }>;
  };
  events?: JsonEvent[];
}

interface ExpectedAgentSource {
  source: "span" | "tool";
  span_id?: string;
}

interface ExpectedBranch {
  forked_at: string;
  event_uuids: string[];
}

interface ExpectedAgent {
  id: string;
  name: string;
  source: ExpectedAgentSource;
  event_uuids?: string[];
  nested_uuids?: string[];
  branches?: ExpectedBranch[];
  children?: ExpectedAgent[];
  content_structure?: Array<{
    type: "event" | "agent";
    uuid?: string;
    id?: string;
    name?: string;
    source?: ExpectedAgentSource;
    nested_uuids?: string[];
    total_tokens?: number;
  }>;
  content_types?: string[];
  total_tokens?: number;
  utility?: boolean;
}

interface ExpectedSection {
  section: "init" | "scoring";
  event_uuids: string[];
  total_tokens?: number;
}

interface ExpectedNodes {
  init: ExpectedSection | null;
  agent: ExpectedAgent | null;
  scoring: ExpectedSection | null;
}

interface FixtureData {
  description: string;
  events: JsonEvent[];
  expected: ExpectedNodes;
}

// =============================================================================
// Fixture Loading
// =============================================================================

const FIXTURES_DIR = join(
  __dirname,
  "../../../../../../../tests/transcript/nodes/fixtures/events"
);

function loadFixture(name: string): FixtureData {
  const filePath = join(FIXTURES_DIR, `${name}.json`);
  const content = readFileSync(filePath, "utf-8");
  return JSON.parse(content) as FixtureData;
}

function getFixtureNames(): string[] {
  const files = readdirSync(FIXTURES_DIR);
  return files
    .filter((f) => f.endsWith(".json"))
    .map((f) => f.replace(".json", ""));
}

// =============================================================================
// Event Deserialization
// =============================================================================

/**
 * Convert minimal JSON event to Event object.
 *
 * The fixtures use minimal representations; this creates Event objects
 * with just the fields needed for our node building logic.
 * We cast to Event since the full type has many required fields we don't need.
 */
function createEvent(data: JsonEvent): Event | null {
  const baseFields = {
    uuid: data.uuid ?? null,
    timestamp: data.timestamp ?? "",
    working_start: 0,
    pending: false,
    metadata: null,
  };

  switch (data.event) {
    case "model": {
      // Create a minimal ModelEvent-like object with just what we need
      // Map input messages to include tool_call_id for tool messages
      const inputMsgs = (data.input ?? []).map((msg) => {
        const mapped: Record<string, unknown> = {
          role: msg.role,
          content: msg.content,
        };
        if (msg.tool_call_id !== undefined) {
          mapped.tool_call_id = msg.tool_call_id;
        }
        return mapped;
      });
      return {
        ...baseFields,
        event: "model",
        model: data.model ?? "unknown",
        completed: data.completed ?? null,
        input: inputMsgs,
        output: data.output
          ? {
              choices: data.output.choices
                ? data.output.choices.map((c) => ({
                    message: {
                      role: c.message.role,
                      content: c.message.content,
                    },
                    stop_reason: c.stop_reason ?? "stop",
                  }))
                : undefined,
              usage: data.output.usage
                ? {
                    input_tokens: data.output.usage.input_tokens ?? 0,
                    output_tokens: data.output.usage.output_tokens ?? 0,
                  }
                : null,
            }
          : null,
      } as Event;
    }

    case "tool": {
      const nestedEvents = data.events
        ?.map((e) => createEvent(e))
        .filter((e): e is Event => e !== null);
      return {
        ...baseFields,
        event: "tool",
        id: data.id ?? "",
        function: data.function ?? "",
        completed: data.completed ?? null,
        agent: data.agent ?? null,
        events: nestedEvents ?? [],
      } as Event;
    }

    case "info": {
      return {
        ...baseFields,
        event: "info",
        source: data.source ?? "unknown",
        data: {},
        span_id: data.span_id ?? null,
      } as Event;
    }

    case "span_begin": {
      return {
        ...baseFields,
        event: "span_begin",
        id: data.id ?? "",
        name: data.name ?? "",
        type: data.type ?? null,
        parent_id: data.parent_id ?? null,
        span_id: data.span_id ?? null,
      } as Event;
    }

    case "span_end": {
      return {
        ...baseFields,
        event: "span_end",
        id: data.id ?? "",
        span_id: data.span_id ?? null,
      } as Event;
    }

    case "compaction": {
      return {
        ...baseFields,
        event: "compaction",
        type: data.type ?? "summary",
        span_id: data.span_id ?? null,
        source: null,
        tokens_before: null,
        tokens_after: null,
      } as Event;
    }

    default:
      // Skip unknown event types
      return null;
  }
}

function eventsFromJson(data: FixtureData): Event[] {
  return data.events
    .map((e) => createEvent(e))
    .filter((e): e is Event => e !== null);
}

// =============================================================================
// Assertion Helpers
// =============================================================================

/**
 * Get direct event UUIDs from a TimelineSpan's content (non-recursive).
 */
function getDirectEventUuids(node: TimelineSpan): string[] {
  return node.content
    .filter((c): c is TimelineEvent => c.type === "event")
    .map((c) => c.event.uuid)
    .filter((uuid): uuid is string => uuid !== null);
}

/**
 * Get child spans from a TimelineSpan.
 */
function getChildSpans(node: TimelineSpan): TimelineSpan[] {
  return node.content.filter((c): c is TimelineSpan => c.type === "span");
}

/**
 * Get all event UUIDs recursively from a TimelineSpan.
 */
function getAllEventUuids(node: TimelineSpan): string[] {
  const uuids: string[] = [];
  for (const item of node.content) {
    if (item.type === "event") {
      if (item.event.uuid) {
        uuids.push(item.event.uuid);
      }
    } else {
      // Recursively collect from child spans
      uuids.push(...getAllEventUuids(item));
    }
  }
  return uuids;
}

/**
 * Assert that a Branch matches expected values.
 */
function assertBranchMatches(
  actual: TimelineBranch,
  expected: ExpectedBranch
): void {
  expect(actual.forkedAt).toBe(expected.forked_at);
  if (expected.event_uuids !== undefined) {
    const uuids = actual.content
      .filter((c): c is TimelineEvent => c.type === "event")
      .map((c) => c.event.uuid)
      .filter((uuid): uuid is string => uuid !== null);
    expect(uuids).toEqual(expected.event_uuids);
  }
}

/**
 * Assert that a scoring span matches expected values.
 *
 * Scoring is now a TimelineSpan with spanType="scorers" in the root's content.
 */
function assertScoringSpanMatches(
  root: TimelineSpan,
  expected: ExpectedSection | null
): void {
  const scorerSpans = root.content.filter(
    (c): c is TimelineSpan => c.type === "span" && c.spanType === "scorers"
  );

  if (expected === null) {
    expect(scorerSpans.length).toBe(0);
    return;
  }

  expect(scorerSpans.length).toBe(1);
  const scoring = scorerSpans[0]!;

  if (expected.event_uuids !== undefined) {
    const actualUuids = getDirectEventUuids(scoring);
    expect(actualUuids).toEqual(expected.event_uuids);
  }
}

/**
 * Assert that a TimelineSpan matches expected values.
 *
 * Maps fixture's AgentSource to spanType:
 * - source: "span" → spanType: "agent"
 * - source: "tool" → spanType: null
 *
 * Maps fixture's content_structure type: "agent" → actual type: "span"
 */
function assertSpanMatches(
  actual: TimelineSpan | null,
  expected: ExpectedAgent | null
): void {
  if (expected === null) {
    expect(actual).toBeNull();
    return;
  }
  expect(actual).not.toBeNull();
  expect(actual!.id).toBe(expected.id);
  expect(actual!.name).toBe(expected.name);

  // Check source → spanType mapping
  if (expected.source.source === "span") {
    expect(actual!.spanType).toBe("agent");
  } else if (expected.source.source === "tool") {
    expect(actual!.spanType).toBeNull();
  }

  // Check event UUIDs if specified
  if (expected.event_uuids !== undefined) {
    const directUuids = getDirectEventUuids(actual!);
    expect(directUuids).toEqual(expected.event_uuids);
  }

  // Check total tokens if specified
  if (expected.total_tokens !== undefined) {
    expect(actual!.totalTokens).toBe(expected.total_tokens);
  }

  // Check utility if specified
  if (expected.utility !== undefined) {
    expect(actual!.utility).toBe(expected.utility);
  }

  // Check branches if specified
  if (expected.branches !== undefined) {
    expect(actual!.branches.length).toBe(expected.branches.length);
    for (let i = 0; i < expected.branches.length; i++) {
      const actualBranch = actual!.branches[i];
      const expectedBranch = expected.branches[i];
      if (actualBranch && expectedBranch) {
        assertBranchMatches(actualBranch, expectedBranch);
      }
    }
  }

  // Check children if specified
  if (expected.children !== undefined) {
    const childSpans = getChildSpans(actual!);
    expect(childSpans.length).toBe(expected.children.length);
    for (let i = 0; i < expected.children.length; i++) {
      const childSpan = childSpans[i];
      const expectedChild = expected.children[i];
      assertSpanMatches(childSpan ?? null, expectedChild ?? null);
    }
  }

  // Check content_structure if specified (for tool-spawned agent tests)
  if (expected.content_structure !== undefined) {
    expect(actual!.content.length).toBe(expected.content_structure.length);
    for (let i = 0; i < expected.content_structure.length; i++) {
      const actualItem = actual!.content[i];
      const expectedItem = expected.content_structure[i];

      if (!actualItem || !expectedItem) {
        continue;
      }

      // Map fixture's "agent" to actual "span"
      const expectedType =
        expectedItem.type === "agent" ? "span" : expectedItem.type;
      expect(actualItem.type).toBe(expectedType);

      if (expectedItem.type === "event" && expectedItem.uuid) {
        expect((actualItem as TimelineEvent).event.uuid).toBe(
          expectedItem.uuid
        );
      }

      if (expectedItem.type === "agent") {
        const spanItem = actualItem as TimelineSpan;
        if (expectedItem.id) {
          expect(spanItem.id).toBe(expectedItem.id);
        }
        if (expectedItem.name) {
          expect(spanItem.name).toBe(expectedItem.name);
        }
        if (expectedItem.source) {
          if (expectedItem.source.source === "span") {
            expect(spanItem.spanType).toBe("agent");
          } else if (expectedItem.source.source === "tool") {
            expect(spanItem.spanType).toBeNull();
          }
        }
        if (expectedItem.nested_uuids) {
          const allUuids = getAllEventUuids(spanItem);
          expect(allUuids).toEqual(expectedItem.nested_uuids);
        }
        if (expectedItem.total_tokens !== undefined) {
          expect(spanItem.totalTokens).toBe(expectedItem.total_tokens);
        }
      }
    }
  }
}

/**
 * Assert that a Timeline matches expected values from the fixture.
 *
 * Maps the old fixture format (init/agent/scoring) to the new Timeline structure:
 * - init events are folded into root content
 * - agent maps to root
 * - scoring maps to a child TimelineSpan with spanType="scorers"
 */
function assertTimelineMatches(
  actual: Timeline,
  expected: ExpectedNodes
): void {
  const root = actual.root;

  // Check init: init events are now in the root content
  if (expected.init !== null) {
    const expectedUuids = expected.init.event_uuids;
    if (expectedUuids.length > 0) {
      const actualInitUuids: string[] = [];
      for (const item of root.content) {
        if (item.type === "event") {
          if (item.event.uuid) {
            actualInitUuids.push(item.event.uuid);
          }
          if (actualInitUuids.length >= expectedUuids.length) {
            break;
          }
        } else {
          break;
        }
      }
      expect(actualInitUuids.slice(0, expectedUuids.length)).toEqual(
        expectedUuids
      );
    }
  }

  // Check agent (now root)
  if (expected.agent !== null) {
    expect(root.id).toBe(expected.agent.id);
    expect(root.name).toBe(expected.agent.name);

    // Check event UUIDs (excluding init events and scoring span)
    if (expected.agent.event_uuids !== undefined) {
      let actualUuids = getDirectEventUuids(root);
      // Filter out init UUIDs if init was present
      if (expected.init !== null) {
        const initUuidSet = new Set(expected.init.event_uuids);
        actualUuids = actualUuids.filter((u) => !initUuidSet.has(u));
      }
      expect(actualUuids).toEqual(expected.agent.event_uuids);
    }

    // Check total tokens if specified (root includes init + scoring)
    if (expected.agent.total_tokens !== undefined) {
      let expectedTokens = expected.agent.total_tokens;
      if (expected.init?.total_tokens) {
        expectedTokens += expected.init.total_tokens;
      }
      if (expected.scoring?.total_tokens) {
        expectedTokens += expected.scoring.total_tokens;
      }
      expect(root.totalTokens).toBe(expectedTokens);
    }

    // Check utility if specified
    if (expected.agent.utility !== undefined) {
      expect(root.utility).toBe(expected.agent.utility);
    }

    // Check branches if specified
    if (expected.agent.branches !== undefined) {
      expect(root.branches.length).toBe(expected.agent.branches.length);
      for (let i = 0; i < expected.agent.branches.length; i++) {
        const actualBranch = root.branches[i];
        const expectedBranch = expected.agent.branches[i];
        if (actualBranch && expectedBranch) {
          assertBranchMatches(actualBranch, expectedBranch);
        }
      }
    }

    // Check children if specified (filter out scorer spans)
    if (expected.agent.children !== undefined) {
      const childSpans = root.content.filter(
        (c): c is TimelineSpan => c.type === "span" && c.spanType !== "scorers"
      );
      expect(childSpans.length).toBe(expected.agent.children.length);
      for (let i = 0; i < expected.agent.children.length; i++) {
        const childSpan = childSpans[i];
        const expectedChild = expected.agent.children[i];
        assertSpanMatches(childSpan ?? null, expectedChild ?? null);
      }
    }

    // Check content_structure if specified
    if (expected.agent.content_structure !== undefined) {
      // Filter out init events and scorer spans from content for structure check
      let contentToCheck = root.content;
      if (expected.init !== null && expected.init.event_uuids.length > 0) {
        const initUuidSet = new Set(expected.init.event_uuids);
        contentToCheck = contentToCheck.filter(
          (item) =>
            !(
              item.type === "event" &&
              item.event.uuid &&
              initUuidSet.has(item.event.uuid)
            )
        );
      }
      // Filter out scorer spans
      contentToCheck = contentToCheck.filter(
        (item) => !(item.type === "span" && item.spanType === "scorers")
      );

      expect(contentToCheck.length).toBe(
        expected.agent.content_structure.length
      );
      for (let i = 0; i < expected.agent.content_structure.length; i++) {
        const actualItem = contentToCheck[i];
        const expectedItem = expected.agent.content_structure[i];

        if (!actualItem || !expectedItem) {
          continue;
        }

        // Map fixture's "agent" to actual "span"
        const expectedType =
          expectedItem.type === "agent" ? "span" : expectedItem.type;
        expect(actualItem.type).toBe(expectedType);

        if (expectedItem.type === "event" && expectedItem.uuid) {
          expect((actualItem as TimelineEvent).event.uuid).toBe(
            expectedItem.uuid
          );
        }

        if (expectedItem.type === "agent") {
          const spanItem = actualItem as TimelineSpan;
          if (expectedItem.id) {
            expect(spanItem.id).toBe(expectedItem.id);
          }
          if (expectedItem.name) {
            expect(spanItem.name).toBe(expectedItem.name);
          }
          if (expectedItem.source) {
            if (expectedItem.source.source === "span") {
              expect(spanItem.spanType).toBe("agent");
            } else if (expectedItem.source.source === "tool") {
              expect(spanItem.spanType).toBeNull();
            }
          }
          if (expectedItem.nested_uuids) {
            const allUuids = getAllEventUuids(spanItem);
            expect(allUuids).toEqual(expectedItem.nested_uuids);
          }
          if (expectedItem.total_tokens !== undefined) {
            expect(spanItem.totalTokens).toBe(expectedItem.total_tokens);
          }
        }
      }
    }
  }

  // Check scoring (now a child TimelineSpan with spanType="scorers")
  assertScoringSpanMatches(root, expected.scoring);
}

// =============================================================================
// Tests
// =============================================================================

describe("buildTimeline", () => {
  const fixtures = getFixtureNames();

  it.each(fixtures)("fixture: %s", (fixtureName) => {
    const fixture = loadFixture(fixtureName);
    const events = eventsFromJson(fixture);
    const result = buildTimeline(events);
    assertTimelineMatches(result, fixture.expected);
  });

  // Additional edge case tests
  it("returns empty structure for empty events array", () => {
    const result = buildTimeline([]);
    expect(result.root).not.toBeNull();
    expect(result.root.content.length).toBe(0);
    expect(result.root.totalTokens).toBe(0);
  });

  it("computes startTime and endTime correctly", () => {
    const fixture = loadFixture("simple_agent");
    const events = eventsFromJson(fixture);
    const result = buildTimeline(events);

    expect(result.root.startTime).toBeDefined();
    expect(result.root.endTime).toBeDefined();
    expect(result.root.startTime.getTime()).toBeLessThanOrEqual(
      result.root.endTime.getTime()
    );
  });
});
