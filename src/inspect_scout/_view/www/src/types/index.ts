import {
  ChatMessageAssistant,
  ChatMessageSystem,
  ChatMessageTool,
  ChatMessageUser,
  ContentImage,
  ContentText,
  Events,
} from "./log";

// Internal Types
export interface Scans {
  results_dir: string;
  scans: Status[];
}

// Scout types dervice from Python types
// TODO: generate with schema
export interface Status {
  complete: boolean;
  spec: ScanSpec;
  location: string;
  summary: Summary;
  errors: Error[];
}

export interface IPCDataframe {
  format: "arrow.feather";
  version: number;
  encoding: "base64";
  data: string;
  column_names: string[];
  row_count: number;
}

export interface Summary {
  scanners: Record<string, ScannerSummary>;
}

export interface Error {
  transcript_id: string;
  scanner: string;
  error: string;
  trqaceback: string;
}

export interface Model {
  model: string;
  config: Record<string, unknown>;
  args: Record<string, unknown>;
}

export interface ScanSpec {
  scan_file?: string;
  scan_id: string;
  scan_name: string;
  scan_args?: Record<string, unknown>;
  timestamp: string;

  model: Model;

  metadata?: Record<string, unknown>;
  options?: Record<string, unknown>;
  packages?: Record<string, unknown>;
  revision?: Record<string, unknown>;

  scanners: Record<string, Scanner>;
  transcripts?: {
    type: string;
    location?: string;
    transcript_ids: Record<string, string | null>;

    // deprecated value for compatibility with old scans
    count?: number;
  };
}

export interface Scanner {
  name: string;
  file: string;
  params: Record<string, unknown>;
}

export interface ScannerSummary {
  scans: number;
  results: number;
  errors: number;
  tokens: number;
  model_usage: Record<string, ModelUsage>;
  validations: Array<boolean | Record<string, boolean>>;
  metrics: Record<string, Record<string, number>>;
}

export interface ModelUsage {
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  input_tokens_cache_write?: number;
  input_tokens_cache_read?: number;
  reasoning_tokens?: number;
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
