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
  AgentNodeType,
  AgentSource,
  buildTranscriptNodes,
  EventNodeType,
  SectionNodeType,
  TranscriptNodes,
} from "./nodes";

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
  output?: {
    usage?: {
      input_tokens?: number;
      output_tokens?: number;
    };
  };
  events?: JsonEvent[];
}

interface ExpectedAgentSource {
  source: "span" | "tool";
  span_id?: string;
}

interface ExpectedAgent {
  id: string;
  name: string;
  source: ExpectedAgentSource;
  event_uuids?: string[];
  nested_uuids?: string[];
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
}

interface ExpectedSection {
  section: "init" | "scoring";
  event_uuids: string[];
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
      return {
        ...baseFields,
        event: "model",
        model: data.model ?? "unknown",
        completed: data.completed ?? null,
        output: data.output
          ? {
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
 * Get all event UUIDs from an EventNode or AgentNode's content (non-recursive).
 */
function getDirectEventUuids(node: EventNodeType | AgentNodeType): string[] {
  if (node.type === "event") {
    return node.event.uuid ? [node.event.uuid] : [];
  }
  return node.content
    .filter((c): c is EventNodeType => c.type === "event")
    .map((c) => c.event.uuid)
    .filter((uuid): uuid is string => uuid !== null);
}

/**
 * Get all event UUIDs from a SectionNode.
 */
function getSectionEventUuids(node: SectionNodeType): string[] {
  return node.content
    .map((c) => c.event.uuid)
    .filter((uuid): uuid is string => uuid !== null);
}

/**
 * Get child agents from an AgentNode.
 */
function getChildAgents(node: AgentNodeType): AgentNodeType[] {
  return node.content.filter((c): c is AgentNodeType => c.type === "agent");
}

/**
 * Get all event UUIDs recursively from an AgentNode.
 */
function getAllEventUuids(node: AgentNodeType): string[] {
  const uuids: string[] = [];
  for (const item of node.content) {
    if (item.type === "event") {
      if (item.event.uuid) {
        uuids.push(item.event.uuid);
      }
    } else {
      // Recursively collect from child agents
      uuids.push(...getAllEventUuids(item));
    }
  }
  return uuids;
}

/**
 * Assert that an AgentSource matches the expected source.
 */
function assertSourceMatches(
  actual: AgentSource,
  expected: ExpectedAgentSource
): void {
  expect(actual.source).toBe(expected.source);
  if (expected.source === "span" && expected.span_id) {
    expect((actual as { spanId?: string }).spanId).toBe(expected.span_id);
  }
}

/**
 * Assert that a SectionNode matches expected values.
 */
function assertSectionMatches(
  actual: SectionNodeType | null,
  expected: ExpectedSection | null
): void {
  if (expected === null) {
    expect(actual).toBeNull();
    return;
  }
  expect(actual).not.toBeNull();
  expect(actual!.section).toBe(expected.section);
  expect(getSectionEventUuids(actual!)).toEqual(expected.event_uuids);
}

/**
 * Assert that an AgentNode matches expected values.
 *
 * This handles various fixture formats:
 * - event_uuids: direct event UUIDs at this level
 * - nested_uuids: all event UUIDs in nested structure
 * - children: child agent assertions
 * - content_structure: detailed content type assertions
 * - total_tokens: token count validation
 */
function assertAgentMatches(
  actual: AgentNodeType | null,
  expected: ExpectedAgent | null
): void {
  if (expected === null) {
    expect(actual).toBeNull();
    return;
  }
  expect(actual).not.toBeNull();
  expect(actual!.id).toBe(expected.id);
  expect(actual!.name).toBe(expected.name);
  assertSourceMatches(actual!.source, expected.source);

  // Check event UUIDs if specified
  if (expected.event_uuids !== undefined) {
    const directUuids = getDirectEventUuids(actual!);
    expect(directUuids).toEqual(expected.event_uuids);
  }

  // Check total tokens if specified
  if (expected.total_tokens !== undefined) {
    expect(actual!.totalTokens).toBe(expected.total_tokens);
  }

  // Check children if specified
  if (expected.children !== undefined) {
    const childAgents = getChildAgents(actual!);
    expect(childAgents.length).toBe(expected.children.length);
    for (let i = 0; i < expected.children.length; i++) {
      const childAgent = childAgents[i];
      const expectedChild = expected.children[i];
      assertAgentMatches(childAgent ?? null, expectedChild ?? null);
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

      expect(actualItem.type).toBe(expectedItem.type);

      if (expectedItem.type === "event" && expectedItem.uuid) {
        expect((actualItem as EventNodeType).event.uuid).toBe(
          expectedItem.uuid
        );
      }

      if (expectedItem.type === "agent") {
        const agentItem = actualItem as AgentNodeType;
        if (expectedItem.id) {
          expect(agentItem.id).toBe(expectedItem.id);
        }
        if (expectedItem.name) {
          expect(agentItem.name).toBe(expectedItem.name);
        }
        if (expectedItem.source) {
          assertSourceMatches(agentItem.source, expectedItem.source);
        }
        if (expectedItem.nested_uuids) {
          const allUuids = getAllEventUuids(agentItem);
          expect(allUuids).toEqual(expectedItem.nested_uuids);
        }
        if (expectedItem.total_tokens !== undefined) {
          expect(agentItem.totalTokens).toBe(expectedItem.total_tokens);
        }
      }
    }
  }
}

/**
 * Assert that TranscriptNodes match expected values.
 */
function assertNodesMatch(
  actual: TranscriptNodes,
  expected: ExpectedNodes
): void {
  assertSectionMatches(actual.init, expected.init);
  assertAgentMatches(actual.agent, expected.agent);
  assertSectionMatches(actual.scoring, expected.scoring);
}

// =============================================================================
// Tests
// =============================================================================

describe("buildTranscriptNodes", () => {
  const fixtures = getFixtureNames();

  it.each(fixtures)("fixture: %s", (fixtureName) => {
    const fixture = loadFixture(fixtureName);
    const events = eventsFromJson(fixture);
    const result = buildTranscriptNodes(events);
    assertNodesMatch(result, fixture.expected);
  });

  // Additional edge case tests
  it("returns empty structure for empty events array", () => {
    const result = buildTranscriptNodes([]);
    expect(result.init).toBeNull();
    expect(result.agent).toBeNull();
    expect(result.scoring).toBeNull();
    expect(result.startTime).toBeNull();
    expect(result.endTime).toBeNull();
    expect(result.totalTokens).toBe(0);
  });

  it("computes startTime and endTime correctly", () => {
    const fixture = loadFixture("simple_agent");
    const events = eventsFromJson(fixture);
    const result = buildTranscriptNodes(events);

    expect(result.startTime).not.toBeNull();
    expect(result.endTime).not.toBeNull();
    expect(result.startTime!.getTime()).toBeLessThanOrEqual(
      result.endTime!.getTime()
    );
  });
});
