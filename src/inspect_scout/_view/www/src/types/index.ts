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

export interface Results extends Status {
  scanners: Record<string, IPCDataframe>;
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

export interface Transcript {
  type: string;
  count: number;
  data: string;
  fields: Array<Record<string, string>>;
}

export interface ScanSpec {
  scan_file: string;
  scan_id: string;
  scan_name: string;
  scan_args: Record<string, unknown>;
  timestamp: string;

  model: Model;

  metadata: Record<string, unknown>;
  options: Record<string, unknown>;
  packages: Record<string, unknown>;
  revision: Record<string, unknown>;

  scanners: Record<string, Scanner>;
  transcripts: Transcript;
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

export interface Transcript {
  messages: ChatMessages;
  events: Events;
}

export interface ContentTool {
  type: "tool";
  content: (ContentImage | ContentText)[];
}
