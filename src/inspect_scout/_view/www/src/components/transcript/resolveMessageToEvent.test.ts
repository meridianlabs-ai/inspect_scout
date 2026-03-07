import { describe, expect, it } from "vitest";

import type { Event } from "../../types/api-types";

import { resolveMessageToEvent } from "./resolveMessageToEvent";
import type { TimelineEvent, TimelineSpan } from "./timeline";

// =============================================================================
// Test helpers — minimal factories for TimelineSpan/TimelineEvent
// =============================================================================

const kBaseDate = new Date("2024-01-01T00:00:00Z");

function makeTimelineEvent(event: Event): TimelineEvent {
  return {
    type: "event",
    event,
    startTime: kBaseDate,
    endTime: kBaseDate,
    totalTokens: 0,
    idleTime: 0,
  };
}

function makeSpan(
  overrides: Partial<TimelineSpan> & {
    id: string;
    content: TimelineSpan["content"];
  }
): TimelineSpan {
  return {
    type: "span",
    name: overrides.name ?? overrides.id,
    spanType: overrides.spanType ?? null,
    branches: [],
    description: undefined,
    utility: false,
    startTime: kBaseDate,
    endTime: kBaseDate,
    totalTokens: 0,
    idleTime: 0,
    ...overrides,
  };
}

function makeRoot(content: TimelineSpan["content"]): TimelineSpan {
  return makeSpan({ id: "root", content, spanType: "root" });
}

function makeModelEvent(opts: {
  uuid: string;
  inputIds?: string[];
  outputId?: string;
  inputToolMessages?: Array<{
    id: string;
    tool_call_id: string;
    role: "tool";
  }>;
}): Event {
  const input: Array<Record<string, unknown>> = [];
  for (const id of opts.inputIds ?? []) {
    input.push({
      id,
      role: "user",
      content: "test",
      source: null,
      metadata: null,
    });
  }
  for (const msg of opts.inputToolMessages ?? []) {
    input.push({
      id: msg.id,
      role: "tool",
      tool_call_id: msg.tool_call_id,
      content: "tool result",
      function: null,
      error: null,
      source: null,
      metadata: null,
    });
  }

  const choices: Array<Record<string, unknown>> = [];
  if (opts.outputId) {
    choices.push({
      message: {
        id: opts.outputId,
        role: "assistant",
        content: "response",
        source: null,
        metadata: null,
        tool_calls: null,
        internal: null,
      },
      stop_reason: "stop",
      logprobs: null,
    });
  }

  return {
    event: "model",
    uuid: opts.uuid,
    model: "test-model",
    input,
    output: {
      model: "test-model",
      choices,
      usage: {
        input_tokens: 0,
        output_tokens: 0,
        total_tokens: 0,
        input_tokens_cache_read: null,
        input_tokens_cache_write: null,
      },
      error: null,
      metadata: null,
      time: null,
      completion: "",
    },
    config: {} as Event & { event: "model" } extends { config: infer C }
      ? C
      : never,
    tools: [],
    tool_choice: "auto",
    timestamp: kBaseDate.toISOString(),
    span_id: null,
    pending: null,
    metadata: null,
    role: null,
    completed: null,
    error: null,
    cache: null,
    call: null,
    retries: null,
    traceback: null,
    working_start: 0,
  } as unknown as Event;
}

function makeToolEvent(opts: {
  uuid: string;
  messageId?: string;
  agentSpanId?: string;
}): Event {
  return {
    event: "tool",
    uuid: opts.uuid,
    id: `tool-call-${opts.uuid}`,
    function: "test_tool",
    message_id: opts.messageId ?? null,
    agent_span_id: opts.agentSpanId ?? null,
    result: "tool result text",
    span_id: null,
    pending: null,
    metadata: null,
    timestamp: kBaseDate.toISOString(),
    completed: null,
    error: null,
    events: [],
    failed: null,
    truncated: null,
    view: null,
    working_start: 0,
  } as unknown as Event;
}

// =============================================================================
// Tests
// =============================================================================

describe("resolveMessageToEvent", () => {
  describe("Case 1: direct content matches", () => {
    it("matches ModelEvent output message ID", () => {
      const model = makeModelEvent({
        uuid: "model-1",
        outputId: "msg-out-1",
      });
      const root = makeRoot([makeTimelineEvent(model)]);

      const result = resolveMessageToEvent("msg-out-1", root);

      expect(result).toEqual({
        eventId: "model-1",
        agentSpanId: null,
      });
    });

    it("matches ToolEvent.message_id", () => {
      const tool = makeToolEvent({
        uuid: "tool-1",
        messageId: "msg-tool-1",
      });
      const root = makeRoot([makeTimelineEvent(tool)]);

      const result = resolveMessageToEvent("msg-tool-1", root);

      expect(result).toEqual({
        eventId: "tool-1",
        agentSpanId: null,
      });
    });

    it("matches ModelEvent input message ID", () => {
      const model = makeModelEvent({
        uuid: "model-1",
        inputIds: ["msg-input-1"],
      });
      const root = makeRoot([makeTimelineEvent(model)]);

      const result = resolveMessageToEvent("msg-input-1", root);

      expect(result).toEqual({
        eventId: "model-1",
        agentSpanId: null,
      });
    });

    it("returns undefined when no match", () => {
      const model = makeModelEvent({
        uuid: "model-1",
        inputIds: ["msg-a"],
        outputId: "msg-b",
      });
      const root = makeRoot([makeTimelineEvent(model)]);

      expect(resolveMessageToEvent("msg-nonexistent", root)).toBeUndefined();
    });

    it("returns undefined for empty root", () => {
      const root = makeRoot([]);
      expect(resolveMessageToEvent("msg-1", root)).toBeUndefined();
    });

    it("skips events with null uuids", () => {
      const model = makeModelEvent({
        uuid: "model-1",
        outputId: "msg-out-1",
      });
      // Override uuid to null
      (model as Record<string, unknown>).uuid = null;
      const root = makeRoot([makeTimelineEvent(model)]);

      expect(resolveMessageToEvent("msg-out-1", root)).toBeUndefined();
    });
  });

  describe("priority ordering", () => {
    it("output wins over input for same message ID", () => {
      // Model event where the same message ID appears in both input and output
      const model = makeModelEvent({
        uuid: "model-1",
        inputIds: ["msg-1"],
        outputId: "msg-1",
      });
      const root = makeRoot([makeTimelineEvent(model)]);

      const result = resolveMessageToEvent("msg-1", root);

      expect(result).toEqual({
        eventId: "model-1",
        agentSpanId: null,
      });
    });

    it("output wins over tool message_id", () => {
      const model = makeModelEvent({
        uuid: "model-1",
        outputId: "msg-1",
      });
      const tool = makeToolEvent({
        uuid: "tool-1",
        messageId: "msg-1",
      });
      const root = makeRoot([
        makeTimelineEvent(tool),
        makeTimelineEvent(model),
      ]);

      const result = resolveMessageToEvent("msg-1", root);

      expect(result).toEqual({
        eventId: "model-1",
        agentSpanId: null,
      });
    });

    it("tool message_id wins over model input", () => {
      const model = makeModelEvent({
        uuid: "model-1",
        inputIds: ["msg-1"],
      });
      const tool = makeToolEvent({
        uuid: "tool-1",
        messageId: "msg-1",
      });
      const root = makeRoot([
        makeTimelineEvent(model),
        makeTimelineEvent(tool),
      ]);

      const result = resolveMessageToEvent("msg-1", root);

      expect(result).toEqual({
        eventId: "tool-1",
        agentSpanId: null,
      });
    });
  });

  describe("Case 2: agent card result", () => {
    it("detects agent card result via ToolEvent.agent_span_id (span-based flow)", () => {
      const agentSpan = makeSpan({
        id: "agent-span-1",
        spanType: "agent",
        content: [
          makeTimelineEvent(
            makeModelEvent({ uuid: "inner-model-1", outputId: "msg-inner" })
          ),
        ],
      });
      const tool = makeToolEvent({
        uuid: "tool-1",
        messageId: "msg-tool-result",
        agentSpanId: "agent-span-1",
      });
      const root = makeRoot([agentSpan, makeTimelineEvent(tool)]);

      const result = resolveMessageToEvent("msg-tool-result", root);

      expect(result).toEqual({
        eventId: "agent-span-1",
        agentSpanId: null,
      });
    });

    it("detects agent card result via bridge flow (tool_call_id)", () => {
      const agentSpan = makeSpan({
        id: "agent-tc123",
        spanType: "agent",
        content: [
          makeTimelineEvent(
            makeModelEvent({ uuid: "inner-model-1", outputId: "msg-inner" })
          ),
        ],
      });
      const model = makeModelEvent({
        uuid: "model-after",
        inputToolMessages: [
          { id: "msg-bridge-result", tool_call_id: "tc123", role: "tool" },
        ],
      });
      const root = makeRoot([agentSpan, makeTimelineEvent(model)]);

      const result = resolveMessageToEvent("msg-bridge-result", root);

      expect(result).toEqual({
        eventId: "agent-tc123",
        agentSpanId: null,
      });
    });

    it("agent card result wins over model input match for same message", () => {
      // The tool message that becomes the agent card result also appears
      // as a model event input. Agent card result should win.
      const agentSpan = makeSpan({
        id: "agent-tc456",
        spanType: "agent",
        content: [],
      });
      const model = makeModelEvent({
        uuid: "model-after",
        inputToolMessages: [
          { id: "msg-result", tool_call_id: "tc456", role: "tool" },
        ],
        inputIds: [],
      });
      const root = makeRoot([agentSpan, makeTimelineEvent(model)]);

      const result = resolveMessageToEvent("msg-result", root);

      expect(result).toEqual({
        eventId: "agent-tc456",
        agentSpanId: null,
      });
    });
  });

  describe("Case 3: match inside subagent", () => {
    it("returns agentSpanId for match inside child agent span", () => {
      const innerModel = makeModelEvent({
        uuid: "inner-model-1",
        outputId: "msg-inner-out",
      });
      const agentSpan = makeSpan({
        id: "agent-abc",
        spanType: "agent",
        content: [makeTimelineEvent(innerModel)],
      });
      const root = makeRoot([agentSpan]);

      const result = resolveMessageToEvent("msg-inner-out", root);

      expect(result).toEqual({
        eventId: "inner-model-1",
        agentSpanId: "agent-abc",
      });
    });

    it("deeply nested agent uses first agent below root as agentSpanId", () => {
      const deepModel = makeModelEvent({
        uuid: "deep-model",
        outputId: "msg-deep",
      });
      const innerAgent = makeSpan({
        id: "inner-agent",
        spanType: "agent",
        content: [makeTimelineEvent(deepModel)],
      });
      const outerAgent = makeSpan({
        id: "outer-agent",
        spanType: "agent",
        content: [innerAgent],
      });
      const root = makeRoot([outerAgent]);

      const result = resolveMessageToEvent("msg-deep", root);

      expect(result).toEqual({
        eventId: "deep-model",
        agentSpanId: "outer-agent",
      });
    });
  });

  describe("transparent non-agent spans", () => {
    it("events in non-agent spans are treated as root-level", () => {
      const model = makeModelEvent({
        uuid: "model-in-scoring",
        outputId: "msg-score-out",
      });
      const scoringSpan = makeSpan({
        id: "scoring-span",
        spanType: "scorer",
        content: [makeTimelineEvent(model)],
      });
      const root = makeRoot([scoringSpan]);

      const result = resolveMessageToEvent("msg-score-out", root);

      expect(result).toEqual({
        eventId: "model-in-scoring",
        agentSpanId: null,
      });
    });

    it("events in init span inside agent still reference the agent", () => {
      const model = makeModelEvent({
        uuid: "model-in-init",
        outputId: "msg-init-out",
      });
      const initSpan = makeSpan({
        id: "init-span",
        spanType: "init",
        content: [makeTimelineEvent(model)],
      });
      const agentSpan = makeSpan({
        id: "agent-xyz",
        spanType: "agent",
        content: [initSpan],
      });
      const root = makeRoot([agentSpan]);

      const result = resolveMessageToEvent("msg-init-out", root);

      expect(result).toEqual({
        eventId: "model-in-init",
        agentSpanId: "agent-xyz",
      });
    });
  });

  describe("Case 4: tool_call_id bridge", () => {
    it("redirects tool-role model input to the sibling ToolEvent that produced it", () => {
      // A tool-role message in the model's input has a tool_call_id that
      // matches a sibling ToolEvent's id. The resolver should point to
      // the ToolEvent rather than the model event.
      const tool = makeToolEvent({
        uuid: "tool-bash",
        // No messageId set — this is the common case where ToolEvent.message_id is null
      });
      // Override the tool call id to match what the model input references
      (tool as Record<string, unknown>).id = "tc-bash-123";

      const model = makeModelEvent({
        uuid: "model-after",
        inputToolMessages: [
          { id: "msg-tool-result", tool_call_id: "tc-bash-123", role: "tool" },
        ],
      });
      const root = makeRoot([
        makeTimelineEvent(tool),
        makeTimelineEvent(model),
      ]);

      const result = resolveMessageToEvent("msg-tool-result", root);

      expect(result).toEqual({
        eventId: "tool-bash",
        agentSpanId: null,
      });
    });

    it("agent card result wins over tool_call_id bridge", () => {
      // When the tool_call_id maps to an agent span, agent card result
      // (priority 2) should win over tool_call_id bridge (priority 3.5)
      const agentSpan = makeSpan({
        id: "agent-tc456",
        spanType: "agent",
        content: [],
      });
      const tool = makeToolEvent({ uuid: "tool-456" });
      (tool as Record<string, unknown>).id = "tc456";

      const model = makeModelEvent({
        uuid: "model-after",
        inputToolMessages: [
          { id: "msg-result", tool_call_id: "tc456", role: "tool" },
        ],
      });
      const root = makeRoot([
        agentSpan,
        makeTimelineEvent(tool),
        makeTimelineEvent(model),
      ]);

      const result = resolveMessageToEvent("msg-result", root);

      expect(result).toEqual({
        eventId: "agent-tc456",
        agentSpanId: null,
      });
    });

    it("tool_call_id bridge wins over model input for same message", () => {
      // When the tool_call_id points to a real ToolEvent (not an agent),
      // the bridge match (3.5) should win over plain model input (4).
      const tool = makeToolEvent({ uuid: "tool-xyz" });
      (tool as Record<string, unknown>).id = "tc-xyz";

      const model1 = makeModelEvent({
        uuid: "model-1",
        inputToolMessages: [
          { id: "msg-bridge", tool_call_id: "tc-xyz", role: "tool" },
        ],
      });
      // A second model event also has the same message in its input
      const model2 = makeModelEvent({
        uuid: "model-2",
        inputIds: ["msg-bridge"],
      });
      const root = makeRoot([
        makeTimelineEvent(tool),
        makeTimelineEvent(model1),
        makeTimelineEvent(model2),
      ]);

      const result = resolveMessageToEvent("msg-bridge", root);

      expect(result).toEqual({
        eventId: "tool-xyz",
        agentSpanId: null,
      });
    });
  });

  describe("edge cases", () => {
    it("ToolEvent without uuid is skipped", () => {
      const tool = makeToolEvent({
        uuid: "tool-1",
        messageId: "msg-1",
      });
      (tool as Record<string, unknown>).uuid = null;
      const root = makeRoot([makeTimelineEvent(tool)]);

      expect(resolveMessageToEvent("msg-1", root)).toBeUndefined();
    });

    it("agent card result inside parent agent sets agentSpanId to parent", () => {
      // An agent card within another agent — scroll to the nested agent card,
      // but select the parent agent's swimlane first.
      const innerAgent = makeSpan({
        id: "inner-agent",
        spanType: "agent",
        content: [],
      });
      const tool = makeToolEvent({
        uuid: "tool-inner",
        messageId: "msg-inner-result",
        agentSpanId: "inner-agent",
      });
      const outerAgent = makeSpan({
        id: "outer-agent",
        spanType: "agent",
        content: [innerAgent, makeTimelineEvent(tool)],
      });
      const root = makeRoot([outerAgent]);

      const result = resolveMessageToEvent("msg-inner-result", root);

      expect(result).toEqual({
        eventId: "inner-agent",
        agentSpanId: "outer-agent",
      });
    });
  });
});
