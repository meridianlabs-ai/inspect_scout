import {
  ChatMessageAssistant,
  ChatMessageSystem,
  ChatMessageTool,
  ChatMessageUser,
  ContentImage,
  ContentText,
  Event,
  Score,
} from "./api-types";

// Scout types generated from OpenAPI schema
// To regenerate: .venv/bin/python scripts/export_openapi_schema.py
export type {
  Status,
  ScanSpec,
  Summary,
  Error,
  ScannerSpec as Scanner,
  ScannerSummary,
  ModelConfig as Model,
} from "./api-types";

// Query builder
export {
  transcriptColumns,
  Column,
  ConditionBuilder,
  TranscriptColumns,
} from "../query";
export type { ConditionModel, ScalarValue } from "../query";

export interface IPCDataframe {
  format: "arrow.feather";
  version: number;
  encoding: "base64";
  data: string;
  column_names: string[];
  row_count: number;
}

export type ChatMessages = ChatMessage[];

export type ChatMessage =
  | ChatMessageSystem
  | ChatMessageUser
  | ChatMessageAssistant
  | ChatMessageTool;

export interface TranscriptInfo {
  agent?: string;
  agent_args?: string;
  date?: string;
  error?: string;
  limit?: string;

  metadata: TranscriptMetadata;

  model?: string;
  model_options?: string;

  score?: Score;

  source_id: string;
  source_type: string;
  source_uri: string;

  success?: boolean;

  task_id?: string;
  task_repeat?: number;
  task_set?: string;

  total_time?: number;
  total_tokens?: number;

  transcript_id: string;
}

export interface Transcript extends TranscriptInfo {
  messages: ChatMessages;
  events: Event[];
}

export interface TranscriptMetadata {
  // These fields are only left here as optional for backwards compatbility
  // for scans which were run before these fields were added to the Transcript data itself
  // we will still scrounge around for them if we can't resolve them from
  // the Transcript directly
  sample_id?: string;
  id?: string | number;
  epoch?: number;
  eval_id?: string;
  log?: string;
  date?: string;
  eval_metadata?: Record<string, unknown>;
  task?: string;
  task_name?: string;
  model?: string;
  score?: string;
  [key: string]: unknown;
}

export interface ContentTool {
  type: "tool";
  content: (ContentImage | ContentText)[];
}
