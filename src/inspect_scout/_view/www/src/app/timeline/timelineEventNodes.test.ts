import { describe, expect, it } from "vitest";

import type {
  TimelineEvent,
  TimelineSpan,
} from "../../components/transcript/timeline";
import { EventNode } from "../../components/transcript/types";
import type { SpanBeginEvent, ToolEvent } from "../../types/api-types";

import { makeSpan, ts } from "./testHelpers";
import { collectRawEvents, attachSourceSpans } from "./timelineEventNodes";

// =============================================================================
// Test helpers
// =============================================================================

function makeToolTimelineEvent(
  id: string,
  startSec: number,
  options?: { agent_span_id?: string | null }
): TimelineEvent {
  const event: ToolEvent = {
    event: "tool",
    type: "function",
    function: "test_tool",
    id,
    arguments: {},
    result: "ok",
    events: [],
    timestamp: ts(startSec).toISOString(),
    working_start: startSec,
    working_time: 1,
    error: null,
    failed: null,
    agent: null,
    agent_span_id: options?.agent_span_id ?? null,
    completed: null,
    message_id: null,
    metadata: null,
    pending: null,
    span_id: null,
    truncated: null,
    uuid: null,
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

function makeAgentSpan(
  id: string,
  startSec: number,
  endSec: number,
  content: TimelineSpan["content"] = []
): TimelineSpan {
  return makeSpan(id, startSec, endSec, 100, content, { spanType: "agent" });
}

// =============================================================================
// collectRawEvents – tool-event-to-agent-span matching
// =============================================================================

describe("collectRawEvents", () => {
  describe("tool event look-ahead matching", () => {
    it("suppresses ToolEvent with agent_span_id matching next agent span", () => {
      const tool = makeToolTimelineEvent("call-1", 0, {
        agent_span_id: "my-agent",
      });
      const span = makeAgentSpan("my-agent", 1, 5);
      const root = makeSpan("Root", 0, 10, 200, [tool, span]);

      const { events, agentToolEvents } = collectRawEvents([root]);

      // ToolEvent should be suppressed (not in events)
      const toolEvents = events.filter((e) => e.event === "tool");
      expect(toolEvents).toHaveLength(0);

      // Should be stored in agentToolEvents keyed by span ID
      expect(agentToolEvents.get("my-agent")).toBe(tool.event);
    });

    it("suppresses ToolEvent with legacy agent-{id} convention", () => {
      const tool = makeToolTimelineEvent("call-1", 0);
      const span = makeAgentSpan("agent-call-1", 1, 5);
      const root = makeSpan("Root", 0, 10, 200, [tool, span]);

      const { events, agentToolEvents } = collectRawEvents([root]);

      const toolEvents = events.filter((e) => e.event === "tool");
      expect(toolEvents).toHaveLength(0);
      expect(agentToolEvents.get("agent-call-1")).toBe(tool.event);
    });

    it("emits ToolEvent when next agent span has non-matching ID", () => {
      const tool = makeToolTimelineEvent("call-1", 0, {
        agent_span_id: "other-agent",
      });
      const span = makeAgentSpan("different-agent", 1, 5);
      const root = makeSpan("Root", 0, 10, 200, [tool, span]);

      const { events, agentToolEvents } = collectRawEvents([root]);

      const toolEvents = events.filter((e) => e.event === "tool");
      expect(toolEvents).toHaveLength(1);
      expect(agentToolEvents.size).toBe(0);
    });

    it("emits ToolEvent when not followed by any span", () => {
      const tool = makeToolTimelineEvent("call-1", 0);
      const root = makeSpan("Root", 0, 10, 200, [tool]);

      const { events, agentToolEvents } = collectRawEvents([root]);

      const toolEvents = events.filter((e) => e.event === "tool");
      expect(toolEvents).toHaveLength(1);
      expect(agentToolEvents.size).toBe(0);
    });

    it("emits ToolEvent when followed by a non-agent span", () => {
      const tool = makeToolTimelineEvent("call-1", 0);
      const nonAgentSpan = makeSpan("scorer", 1, 5, 50, [], {
        spanType: "scorer",
      });
      const root = makeSpan("Root", 0, 10, 200, [tool, nonAgentSpan]);

      const { events, agentToolEvents } = collectRawEvents([root]);

      const toolEvents = events.filter((e) => e.event === "tool");
      expect(toolEvents).toHaveLength(1);
      expect(agentToolEvents.size).toBe(0);
    });
  });
});

// =============================================================================
// attachSourceSpans – agentToolEvent attachment
// =============================================================================

describe("attachSourceSpans", () => {
  it("sets agentToolEvent on span_begin node matching agentToolEvents entry", () => {
    const spanBegin: SpanBeginEvent = {
      event: "span_begin",
      name: "Agent",
      id: "agent-1",
      span_id: "agent-1",
      type: "agent",
      timestamp: ts(0).toISOString(),
      parent_id: null,
      pending: false,
      working_start: 0,
      uuid: null,
      metadata: null,
    };
    const node = new EventNode("agent-1", spanBegin, 0);

    const toolEvent: ToolEvent = {
      event: "tool",
      type: "function",
      function: "test_tool",
      id: "call-1",
      arguments: {},
      result: "ok",
      events: [],
      timestamp: ts(0).toISOString(),
      working_start: 0,
      working_time: 1,
      error: null,
      failed: null,
      agent: null,
      agent_span_id: "agent-1",
      completed: null,
      message_id: null,
      metadata: null,
      pending: null,
      span_id: null,
      truncated: null,
      uuid: null,
      view: null,
    };

    const spanMap = new Map<string, TimelineSpan>();
    const agentToolEvents = new Map<string, ToolEvent>([
      ["agent-1", toolEvent],
    ]);

    attachSourceSpans([node], spanMap, agentToolEvents);

    expect(node.agentToolEvent).toBe(toolEvent);
  });

  it("leaves agentToolEvent undefined when no matching entry exists", () => {
    const spanBegin: SpanBeginEvent = {
      event: "span_begin",
      name: "Agent",
      id: "agent-2",
      span_id: "agent-2",
      type: "agent",
      timestamp: ts(0).toISOString(),
      parent_id: null,
      pending: false,
      working_start: 0,
      uuid: null,
      metadata: null,
    };
    const node = new EventNode("agent-2", spanBegin, 0);

    const spanMap = new Map<string, TimelineSpan>();
    const agentToolEvents = new Map<string, ToolEvent>();

    attachSourceSpans([node], spanMap, agentToolEvents);

    expect(node.agentToolEvent).toBeUndefined();
  });
});
