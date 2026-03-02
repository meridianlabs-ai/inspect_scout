import {
  ApprovalEvent,
  CompactionEvent,
  JsonChange,
  ErrorEvent,
  InfoEvent,
  InputEvent,
  LoggerEvent,
  ModelEvent,
  SampleInitEvent,
  SampleLimitEvent,
  SandboxEvent,
  ScoreEvent,
  ScoreEditEvent,
  SpanBeginEvent,
  SpanEndEvent,
  StateEvent,
  StepEvent,
  StoreEvent,
  SubtaskEvent,
  ToolEvent,
} from "../../types/api-types";

import type { TimelineSpan } from "./timeline";
import { STEP, SPAN_BEGIN, TYPE_TOOL, TYPE_SUBTASK } from "./transform/utils";

export interface StateManager {
  scope: string;
  getState(): object;
  initializeState(state: object): void;
  applyChanges(changes: JsonChange[]): object;
}

export const kTranscriptCollapseScope = "transcript-collapse";
export const kTranscriptOutlineCollapseScope = "transcript-outline";

export const kCollapsibleEventTypes = [
  STEP,
  SPAN_BEGIN,
  TYPE_TOOL,
  TYPE_SUBTASK,
];

export type EventType =
  | SampleInitEvent
  | SampleLimitEvent
  | StateEvent
  | StoreEvent
  | ModelEvent
  | LoggerEvent
  | InfoEvent
  | StepEvent
  | SubtaskEvent
  | ScoreEvent
  | ScoreEditEvent
  | ToolEvent
  | InputEvent
  | ErrorEvent
  | ApprovalEvent
  | CompactionEvent
  | SandboxEvent
  | SpanBeginEvent
  | SpanEndEvent;

// Define the runtime array of all event type values
export const eventTypeValues = [
  "sample_init",
  "sample_limit",
  "state",
  "store",
  "model",
  "logger",
  "info",
  "step",
  "subtask",
  "score",
  "score_edit",
  "tool",
  "input",
  "error",
  "approval",
  "compaction",
  "sandbox",
  "span_begin",
  "span_end",
] as const;

// Derive the type from the array (replaces the indexed access approach)
export type EventTypeValue = (typeof eventTypeValues)[number];
export class EventNode<T extends EventType = EventType> {
  id: string;
  event: T;
  children: EventNode<EventType>[] = [];
  depth: number;
  /** The TimelineSpan this node was synthesized from, if any. */
  sourceSpan?: TimelineSpan;

  constructor(id: string, event: T, depth: number) {
    this.id = id;
    this.event = event;
    this.depth = depth;
  }
}

export interface TranscriptEventState {
  selectedNav?: string;
  collapsed?: boolean;
}

export type TranscriptState = Record<string, TranscriptEventState>;
