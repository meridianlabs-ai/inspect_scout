import { describe, expect, it } from "vitest";

import type {
  ChatMessage,
  ChatMessageAssistant,
  ChatMessageUser,
  Event,
  ModelEvent,
  EventsData,
} from "../../types/api-types";

import { expandEvents } from "./expandEvents";

// -- Helpers for building test fixtures --

const makeUserMsg = (content: string): ChatMessageUser => ({
  role: "user",
  content,
  id: null,
  metadata: null,
  source: null,
  tool_call_id: null,
});

const makeAssistantMsg = (content: string): ChatMessageAssistant => ({
  role: "assistant",
  content,
  id: null,
  metadata: null,
  model: null,
  source: null,
  tool_calls: null,
});

const EMPTY_CONFIG: ModelEvent["config"] = {
  attempt_timeout: null,
  batch: null,
  best_of: null,
  cache: null,
  cache_prompt: null,
  effort: null,
  extra_body: null,
  extra_headers: null,
  frequency_penalty: null,
  internal_tools: null,
  logit_bias: null,
  logprobs: null,
  max_connections: null,
  max_retries: null,
  max_tokens: null,
  max_tool_output: null,
  modalities: null,
  num_choices: null,
  parallel_tool_calls: null,
  presence_penalty: null,
  reasoning_effort: null,
  reasoning_history: null,
  reasoning_summary: null,
  reasoning_tokens: null,
  response_schema: null,
  seed: null,
  stop_seqs: null,
  system_message: null,
  temperature: null,
  timeout: null,
  top_k: null,
  top_logprobs: null,
  top_p: null,
  verbosity: null,
};

const EMPTY_OUTPUT: ModelEvent["output"] = {
  choices: [],
  completion: "",
  model: "test-model",
  error: null,
  metadata: null,
  time: null,
  usage: null,
};

/** Minimal ModelEvent with condensed input_refs (no inline input). */
const makeCondensedModelEvent = (
  inputRefs: [number, number][] | null,
  callOverrides?: Partial<ModelEvent["call"]>
): ModelEvent => ({
  event: "model",
  model: "test-model",
  input: [],
  input_refs: inputRefs,
  output: EMPTY_OUTPUT,
  config: EMPTY_CONFIG,
  call: callOverrides
    ? {
        request: {},
        response: null,
        call_refs: null,
        call_key: null,
        time: null,
        error: null,
        ...callOverrides,
      }
    : null,
  cache: null,
  completed: null,
  error: null,
  metadata: null,
  pending: null,
  retries: null,
  role: null,
  span_id: null,
  timestamp: "2024-01-01T00:00:00Z",
  tool_choice: "auto",
  tools: [],
  traceback: null,
  traceback_ansi: null,
  uuid: null,
  working_start: 0,
  working_time: null,
});

const makeStepEvent = (): Event => ({
  event: "step",
  action: "begin",
  type: null,
  name: "test-step",
  timestamp: "2024-01-01T00:00:00Z",
  metadata: null,
  pending: null,
  span_id: null,
  uuid: null,
  working_start: 0,
});

const pool: ChatMessage[] = [
  makeUserMsg("msg-0"),
  makeUserMsg("msg-1"),
  makeAssistantMsg("msg-2"),
  makeUserMsg("msg-3"),
  makeAssistantMsg("msg-4"),
  makeUserMsg("msg-5"),
  makeAssistantMsg("msg-6"),
];

const callPool: EventsData["calls"] = [
  { role: "user", content: "call-0" },
  { role: "assistant", content: "call-1" },
  { role: "user", content: "call-2" },
  { role: "assistant", content: "call-3" },
  { role: "user", content: "call-4" },
];

describe("expandEvents", () => {
  it("returns events unchanged when eventsData is null", () => {
    const events: Event[] = [makeCondensedModelEvent(null)];
    const result = expandEvents(events, null);
    expect(result).toBe(events);
  });

  it("returns events unchanged when pools are empty", () => {
    const events: Event[] = [makeCondensedModelEvent([[0, 2]])];
    const eventsData: EventsData = { messages: [], calls: [] };
    const result = expandEvents(events, eventsData);
    expect(result).toBe(events);
  });

  it("passes non-ModelEvents through untouched", () => {
    const step = makeStepEvent();
    const eventsData: EventsData = { messages: pool, calls: [] };
    const result = expandEvents([step], eventsData);
    expect(result[0]).toBe(step);
  });

  it("returns ModelEvent unchanged when it has no refs", () => {
    const event = makeCondensedModelEvent(null);
    const eventsData: EventsData = { messages: pool, calls: [] };
    const result = expandEvents([event], eventsData);
    expect(result[0]).toBe(event);
  });

  it("expands input_refs from message pool", () => {
    const event = makeCondensedModelEvent([[0, 3]]);
    const eventsData: EventsData = { messages: pool, calls: [] };
    const result = expandEvents([event], eventsData);
    const expanded = result[0] as ModelEvent;

    expect(expanded.input).toEqual([pool[0], pool[1], pool[2]]);
    expect(expanded.input_refs).toBeNull();
  });

  it("expands multiple non-contiguous input_refs ranges", () => {
    const event = makeCondensedModelEvent([
      [0, 2],
      [5, 7],
    ]);
    const eventsData: EventsData = { messages: pool, calls: [] };
    const result = expandEvents([event], eventsData);
    const expanded = result[0] as ModelEvent;

    expect(expanded.input).toEqual([pool[0], pool[1], pool[5], pool[6]]);
    expect(expanded.input_refs).toBeNull();
  });

  it("expands call_refs from call pool using default key 'messages'", () => {
    const event = makeCondensedModelEvent(null, {
      call_refs: [[0, 3]],
      call_key: null,
      request: { model: "gpt-4" },
    });
    const eventsData: EventsData = { messages: [], calls: callPool };
    const result = expandEvents([event], eventsData);
    const expanded = result[0] as ModelEvent;

    expect(expanded.call?.request).toEqual({
      model: "gpt-4",
      messages: [callPool[0], callPool[1], callPool[2]],
    });
    expect(expanded.call?.call_refs).toBeNull();
    expect(expanded.call?.call_key).toBeNull();
  });

  it("expands call_refs using custom call_key", () => {
    const event = makeCondensedModelEvent(null, {
      call_refs: [[1, 4]],
      call_key: "contents",
      request: { model: "gemini" },
    });
    const eventsData: EventsData = { messages: [], calls: callPool };
    const result = expandEvents([event], eventsData);
    const expanded = result[0] as ModelEvent;

    expect(expanded.call?.request).toEqual({
      model: "gemini",
      contents: [callPool[1], callPool[2], callPool[3]],
    });
    expect(expanded.call?.call_refs).toBeNull();
    expect(expanded.call?.call_key).toBeNull();
  });

  it("expands both input_refs and call_refs in the same event", () => {
    const event = makeCondensedModelEvent([[0, 2]], {
      call_refs: [[0, 2]],
      call_key: null,
      request: {},
    });
    const eventsData: EventsData = { messages: pool, calls: callPool };
    const result = expandEvents([event], eventsData);
    const expanded = result[0] as ModelEvent;

    expect(expanded.input).toEqual([pool[0], pool[1]]);
    expect(expanded.input_refs).toBeNull();
    expect(expanded.call?.request).toEqual({
      messages: [callPool[0], callPool[1]],
    });
    expect(expanded.call?.call_refs).toBeNull();
  });

  it("handles mixed event types preserving order", () => {
    const step = makeStepEvent();
    const model = makeCondensedModelEvent([[0, 1]]);
    const events: Event[] = [step, model, step];
    const eventsData: EventsData = { messages: pool, calls: [] };

    const result = expandEvents(events, eventsData);
    expect(result).toHaveLength(3);
    expect(result[0]).toBe(step);
    expect((result[1] as ModelEvent).input).toEqual([pool[0]]);
    expect(result[2]).toBe(step);
  });

  it("handles single-element ranges", () => {
    const event = makeCondensedModelEvent([
      [2, 3],
      [5, 6],
    ]);
    const eventsData: EventsData = { messages: pool, calls: [] };
    const result = expandEvents([event], eventsData);
    const expanded = result[0] as ModelEvent;

    expect(expanded.input).toEqual([pool[2], pool[5]]);
  });

  it("does not mutate original events", () => {
    const event = makeCondensedModelEvent([[0, 2]]);
    const eventsData: EventsData = { messages: pool, calls: [] };
    expandEvents([event], eventsData);

    expect(event.input).toEqual([]);
    expect(event.input_refs).toEqual([[0, 2]]);
  });
});
