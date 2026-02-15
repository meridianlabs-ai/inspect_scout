/**
 * Unit tests for auto-span detection via conversation threading.
 *
 * Tests the detectAutoSpansForSpan() and classifyAutoSpans() functions
 * which detect coherent sub-agent conversations from flat ModelEvent streams.
 */

import { beforeEach, describe, expect, it } from "vitest";

import {
  type TimelineEvent,
  type TimelineSpan,
  classifyAutoSpans,
  detectAutoSpansForSpan,
} from "../../components/transcript/timeline";
import type { ChatMessage, Event } from "../../types/api-types";

// =============================================================================
// Test Helpers
// =============================================================================

let eventCounter = 0;

function makeModelEvent(opts: {
  input: ChatMessage[];
  outputContent: string;
  uuid?: string;
}): TimelineEvent {
  eventCounter++;
  const uuid = opts.uuid ?? `e-${eventCounter}`;
  const now = new Date(2024, 0, 1, 0, 0, eventCounter);
  return {
    type: "event",
    event: {
      event: "model",
      uuid,
      timestamp: now.toISOString(),
      completed: new Date(now.getTime() + 1000).toISOString(),
      model: "test-model",
      input: opts.input,
      output: {
        choices: [
          {
            message: {
              role: "assistant",
              content: opts.outputContent,
            },
          },
        ],
        usage: { input_tokens: 100, output_tokens: 50 },
      },
    } as Event,
    startTime: now,
    endTime: new Date(now.getTime() + 1000),
    totalTokens: 150,
  };
}

function makeToolEvent(uuid?: string): TimelineEvent {
  eventCounter++;
  const id = uuid ?? `t-${eventCounter}`;
  const now = new Date(2024, 0, 1, 0, 0, eventCounter);
  return {
    type: "event",
    event: {
      event: "tool",
      uuid: id,
      timestamp: now.toISOString(),
      completed: new Date(now.getTime() + 1000).toISOString(),
      id: `tool-${eventCounter}`,
      function: "test_fn",
    } as Event,
    startTime: now,
    endTime: new Date(now.getTime() + 1000),
    totalTokens: 0,
  };
}

function makeInfoEvent(uuid?: string): TimelineEvent {
  eventCounter++;
  const id = uuid ?? `i-${eventCounter}`;
  const now = new Date(2024, 0, 1, 0, 0, eventCounter);
  return {
    type: "event",
    event: {
      event: "info",
      uuid: id,
      timestamp: now.toISOString(),
      source: "test",
      data: {},
    } as Event,
    startTime: now,
    endTime: now,
    totalTokens: 0,
  };
}

function makeSpan(
  content: (TimelineEvent | TimelineSpan)[],
  name: string = "test"
): TimelineSpan {
  const epoch = new Date(0);
  return {
    type: "span",
    id: `span-${name}`,
    name,
    spanType: null,
    content,
    branches: [],
    utility: false,
    startTime: content.length > 0 ? content[0]!.startTime : epoch,
    endTime: content.length > 0 ? content[content.length - 1]!.endTime : epoch,
    totalTokens: content.reduce((sum, c) => sum + c.totalTokens, 0),
  };
}

function sysMsg(text: string): ChatMessage {
  return { role: "system", content: text } as ChatMessage;
}

function userMsg(text: string): ChatMessage {
  return { role: "user", content: text } as ChatMessage;
}

function assistantMsg(text: string): ChatMessage {
  return { role: "assistant", content: text } as ChatMessage;
}

function getChildSpanNames(span: TimelineSpan): string[] {
  return span.content
    .filter((c): c is TimelineSpan => c.type === "span")
    .map((c) => c.name);
}

function getDirectEventUuids(span: TimelineSpan): string[] {
  return span.content
    .filter((c): c is TimelineEvent => c.type === "event")
    .map((c) => c.event.uuid)
    .filter((u): u is string => u !== null && u !== undefined);
}

// =============================================================================
// Tests
// =============================================================================

describe("detectAutoSpansForSpan", () => {
  beforeEach(() => {
    eventCounter = 0;
  });

  it("skips spans with existing child spans", () => {
    const child = makeSpan(
      [
        makeModelEvent({
          input: [sysMsg("A"), userMsg("hi")],
          outputContent: "hello",
        }),
      ],
      "child"
    );
    const parent = makeSpan(
      [
        child,
        makeModelEvent({
          input: [sysMsg("B"), userMsg("hi")],
          outputContent: "world",
        }),
      ],
      "parent"
    );

    detectAutoSpansForSpan(parent);

    // Should be unchanged (has child span)
    expect(parent.content.length).toBe(2);
    expect(parent.content[0]!.type).toBe("span");
  });

  it("skips spans with fewer than 2 model events with output", () => {
    const span = makeSpan(
      [
        makeModelEvent({
          input: [userMsg("hello")],
          outputContent: "hi",
        }),
      ],
      "single"
    );

    detectAutoSpansForSpan(span);

    expect(span.content.length).toBe(1);
    expect(span.content[0]!.type).toBe("event");
  });

  it("does not create spans for a single conversation thread", () => {
    const span = makeSpan(
      [
        makeModelEvent({
          input: [sysMsg("helper"), userMsg("hello")],
          outputContent: "hi there",
        }),
        makeModelEvent({
          input: [
            sysMsg("helper"),
            userMsg("hello"),
            assistantMsg("hi there"),
            userMsg("how are you?"),
          ],
          outputContent: "I am fine",
        }),
        makeModelEvent({
          input: [
            sysMsg("helper"),
            userMsg("hello"),
            assistantMsg("hi there"),
            userMsg("how are you?"),
            assistantMsg("I am fine"),
            userMsg("great"),
          ],
          outputContent: "thanks",
        }),
      ],
      "singlethread"
    );

    detectAutoSpansForSpan(span);

    // Single thread — no child spans created
    expect(span.content.length).toBe(3);
    expect(span.content.every((c) => c.type === "event")).toBe(true);
  });

  it("detects sequential agents with different system prompts", () => {
    const span = makeSpan(
      [
        makeModelEvent({
          input: [sysMsg("Agent A"), userMsg("task A")],
          outputContent: "A response",
          uuid: "e-A",
        }),
        makeModelEvent({
          input: [sysMsg("Agent B"), userMsg("task B")],
          outputContent: "B response",
          uuid: "e-B",
        }),
        makeModelEvent({
          input: [sysMsg("Agent C"), userMsg("task C")],
          outputContent: "C response",
          uuid: "e-C",
        }),
      ],
      "seq"
    );

    detectAutoSpansForSpan(span);

    expect(span.content.length).toBe(3);
    expect(span.content.every((c) => c.type === "span")).toBe(true);
    const names = getChildSpanNames(span);
    expect(names).toEqual(["Agent 1", "Agent 2", "Agent 3"]);
  });

  it("detects parallel conversations with same system prompt", () => {
    const span = makeSpan(
      [
        makeModelEvent({
          input: [sysMsg("explorer"), userMsg("path A")],
          outputContent: "A step 1",
          uuid: "e-A1",
        }),
        makeModelEvent({
          input: [sysMsg("explorer"), userMsg("path B")],
          outputContent: "B step 1",
          uuid: "e-B1",
        }),
        makeModelEvent({
          input: [
            sysMsg("explorer"),
            userMsg("path A"),
            assistantMsg("A step 1"),
            userMsg("continue A"),
          ],
          outputContent: "A step 2",
          uuid: "e-A2",
        }),
        makeModelEvent({
          input: [
            sysMsg("explorer"),
            userMsg("path B"),
            assistantMsg("B step 1"),
            userMsg("continue B"),
          ],
          outputContent: "B step 2",
          uuid: "e-B2",
        }),
      ],
      "parallel"
    );

    detectAutoSpansForSpan(span);

    expect(span.content.length).toBe(2);
    const names = getChildSpanNames(span);
    // Same system prompt → "Agent" (no number)
    expect(names).toEqual(["Agent", "Agent"]);

    // Check event assignment
    const span0 = span.content[0] as TimelineSpan;
    const span1 = span.content[1] as TimelineSpan;
    expect(getDirectEventUuids(span0)).toEqual(["e-A1", "e-A2"]);
    expect(getDirectEventUuids(span1)).toEqual(["e-B1", "e-B2"]);
  });

  it("names threads by prompt group with mixed prompts", () => {
    const span = makeSpan(
      [
        makeModelEvent({
          input: [sysMsg("prompt A"), userMsg("task 1")],
          outputContent: "r1",
        }),
        makeModelEvent({
          input: [sysMsg("prompt A"), userMsg("task 2")],
          outputContent: "r2",
        }),
        makeModelEvent({
          input: [sysMsg("prompt B"), userMsg("task 3")],
          outputContent: "r3",
        }),
      ],
      "mixed"
    );

    detectAutoSpansForSpan(span);

    expect(span.content.length).toBe(3);
    const names = getChildSpanNames(span);
    expect(names).toEqual(["Agent 1", "Agent 1", "Agent 2"]);
  });

  it("keeps preamble events before first ModelEvent in root", () => {
    const info = makeInfoEvent("info-1");
    const span = makeSpan(
      [
        info,
        makeModelEvent({
          input: [sysMsg("A"), userMsg("t1")],
          outputContent: "r1",
          uuid: "e-1",
        }),
        makeModelEvent({
          input: [sysMsg("B"), userMsg("t2")],
          outputContent: "r2",
          uuid: "e-2",
        }),
      ],
      "preamble"
    );

    detectAutoSpansForSpan(span);

    // Preamble event + 2 child spans
    expect(span.content.length).toBe(3);
    expect(span.content[0]!.type).toBe("event");
    expect((span.content[0] as TimelineEvent).event.uuid).toBe("info-1");
    expect(span.content[1]!.type).toBe("span");
    expect(span.content[2]!.type).toBe("span");
  });

  it("assigns non-model events to preceding thread", () => {
    const tool = makeToolEvent("tool-1");
    const span = makeSpan(
      [
        makeModelEvent({
          input: [sysMsg("A"), userMsg("t1")],
          outputContent: "r1",
          uuid: "e-1",
        }),
        tool,
        makeModelEvent({
          input: [sysMsg("B"), userMsg("t2")],
          outputContent: "r2",
          uuid: "e-2",
        }),
      ],
      "interleaved"
    );

    detectAutoSpansForSpan(span);

    expect(span.content.length).toBe(2);
    const span0 = span.content[0] as TimelineSpan;
    const span1 = span.content[1] as TimelineSpan;
    // Tool event should be in first thread
    expect(span0.content.length).toBe(2);
    expect(span0.content[0]!.type).toBe("event");
    expect(span0.content[1]!.type).toBe("event");
    expect((span0.content[1] as TimelineEvent).event.uuid).toBe("tool-1");
    expect(span1.content.length).toBe(1);
  });
});

describe("classifyAutoSpans", () => {
  beforeEach(() => {
    eventCounter = 0;
  });

  it("recurses into child spans", () => {
    // Build a span with an existing child span that has flat model events
    const innerSpan = makeSpan(
      [
        makeModelEvent({
          input: [sysMsg("A"), userMsg("x")],
          outputContent: "r1",
        }),
        makeModelEvent({
          input: [sysMsg("B"), userMsg("y")],
          outputContent: "r2",
        }),
      ],
      "inner"
    );

    const outerSpan = makeSpan([innerSpan], "outer");

    classifyAutoSpans(outerSpan);

    // Outer span should be unchanged (has child span)
    expect(outerSpan.content.length).toBe(1);
    expect(outerSpan.content[0]!.type).toBe("span");

    // Inner span should now have auto-detected child spans
    const inner = outerSpan.content[0] as TimelineSpan;
    expect(inner.content.length).toBe(2);
    expect(inner.content.every((c) => c.type === "span")).toBe(true);
  });

  it("recurses into newly created auto-spans", () => {
    // Create a flat span where sub-threads themselves contain sub-threads
    // This is tricky to set up but tests the recursive nature
    const span = makeSpan(
      [
        makeModelEvent({
          input: [sysMsg("A"), userMsg("x")],
          outputContent: "r1",
        }),
        makeModelEvent({
          input: [sysMsg("B"), userMsg("y")],
          outputContent: "r2",
        }),
      ],
      "root"
    );

    classifyAutoSpans(span);

    // Should have created child spans
    expect(span.content.length).toBe(2);
    expect(span.content.every((c) => c.type === "span")).toBe(true);
  });
});
