import {
  ChatMessageAssistant,
  ChatMessageSystem,
  ChatMessageTool,
  ChatMessageUser,
  ContentImage,
  ContentText,
  Events,
} from "./log";

// Scout types generated from OpenAPI schema
// To regenerate: .venv/bin/python scripts/export_openapi_schema.py
export type {
  Status,
  ScanSpec,
  Summary,
  Error,
  ScannerSpec as Scanner,
  ScannerSummary,
  ModelUsage,
  ModelConfig as Model,
} from "./api-types";

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
  id: string;
  source_id: string;
  source_uri: string;
  source_type: string;
  filename?: string;
  date?: string;
  task_set?: string;
  task_id?: string;
  task_repeat?: number;
  agent?: string;
  agent_args?: string;
  model?: string;
  model_options?: string;
  score?: string;
  success?: boolean;
  total_time?: number;
  total_tokens?: number;
  error?: string;
  limit?: string;
  metadata: TranscriptMetadata;
}

export interface Transcript extends TranscriptInfo {
  messages: ChatMessages;
  events: Events;
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
