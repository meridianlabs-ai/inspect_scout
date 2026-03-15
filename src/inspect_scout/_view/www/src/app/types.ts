import { EventType } from "../components/transcript/types";
import {
  ModelUsage,
  JsonValue,
  ChatMessageSystem,
  ChatMessageUser,
  ChatMessageAssistant,
  ChatMessageTool,
  Event,
  ChatMessage,
  Transcript,
  ScannerInputResponse,
} from "../types/api-types";

export type InputType = ScannerInputResponse["input_type"];

export interface ScanResultSummary {
  // Basic Info
  identifier: string;
  // The original DB result UUID. Shared across expanded resultset rows (e.g.
  // multiple labels from one scan result will have the same uuid but different
  // identifiers). Used to fetch the shared input data for the result.
  uuid?: string;
  explanation?: string;
  label?: string;
  timestamp?: string;

  // Input
  inputType: InputType;

  // Refs
  eventReferences: ScanResultReference[];
  messageReferences: ScanResultReference[];

  // Validation
  validationResult: boolean | Record<string, boolean>;
  validationTarget: JsonValue;

  // Value
  value: string | boolean | number | null | unknown[] | object;
  valueType: ValueType;

  // Scan metadata
  scanError?: string;
  scanErrorRefusal?: boolean;

  // Transcript info
  transcriptSourceId: string;
  transcriptTaskSet?: string;
  transcriptTaskId?: string | number;
  transcriptTaskRepeat?: number;
  transcriptModel?: string;
  transcriptMetadata: Record<string, JsonValue>;
}

// Base interface with common properties
export interface ScanResultData extends ScanResultSummary {
  answer?: string;
  inputIds: string[];
  metadata: Record<string, JsonValue>;
  scanError?: string;
  scanErrorTraceback?: string;
  scanErrorRefusal?: boolean;
  scanEvents: Event[];
  scanId: string;
  scanMetadata: Record<string, JsonValue>;
  scanModelUsage: Record<string, ModelUsage>;
  scanTags: string[];
  scanTotalTokens: number;
  scannerFile: string;
  scannerKey: string;
  scannerName: string;
  scannerParams: Record<string, JsonValue>;
  transcriptId: string;
  transcriptSourceUri: string;

  transcriptDate?: string;
  transcriptAgent?: string;
  transcriptAgentArgs?: Record<string, unknown>;
  transcriptScore?: JsonValue;
  transcriptSuccess?: boolean;
  transcriptMessageCount?: number;
  transcriptTotalTime?: number;
  transcriptTotalTokens?: number;
  transcriptError?: string;
  transcriptLimit?: string;
}

export interface ScanResultReference {
  type: "message" | "event";
  id: string;
  cite?: string;
}

export type MessageType =
  | ChatMessageSystem
  | ChatMessageUser
  | ChatMessageAssistant
  | ChatMessageTool;

export interface SortColumn {
  column: string;
  direction: "asc" | "desc";
}

export type ErrorScope =
  | "scans"
  | "scanner"
  | "dataframe"
  | "dataframe_input"
  | "transcripts";

export type ResultGroup =
  | "source"
  | "label"
  | "id"
  | "epoch"
  | "model"
  | "none";

export type ValueType =
  | "boolean"
  | "number"
  | "string"
  | "array"
  | "object"
  | "null";

// Type guard functions for value types
export function isStringValue(
  result: ScanResultSummary
): result is ScanResultSummary & { valueType: "string"; value: string } {
  return result.valueType === "string";
}

export function isNumberValue(
  result: ScanResultSummary
): result is ScanResultSummary & { valueType: "number"; value: number } {
  return result.valueType === "number";
}

export function isBooleanValue(
  result: ScanResultSummary
): result is ScanResultSummary & { valueType: "boolean"; value: boolean } {
  return result.valueType === "boolean";
}

export function isNullValue(
  result: ScanResultSummary
): result is ScanResultSummary & { valueType: "null"; value: null } {
  return result.valueType === "null";
}

export function isArrayValue(
  result: ScanResultSummary
): result is ScanResultSummary & { valueType: "array"; value: unknown[] } {
  return result.valueType === "array";
}

export function isObjectValue(
  result: ScanResultSummary
): result is ScanResultSummary & { valueType: "object"; value: object } {
  return result.valueType === "object";
}

// Type guard functions for DataFrameInput
export function isTranscriptInput(
  input: ScannerInputResponse
): input is ScannerInputResponse & {
  inputType: "transcript";
  input: Transcript;
} {
  return input.input_type === "transcript";
}

export function isMessageInput(
  input: ScannerInputResponse
): input is ScannerInputResponse & {
  inputType: "message";
  input: MessageType;
} {
  return input.input_type === "message";
}

export function isMessagesInput(
  input: ScannerInputResponse
): input is ScannerInputResponse & {
  inputType: "messages";
  input: ChatMessage[];
} {
  return input.input_type === "messages";
}

export function isEventInput(
  input: ScannerInputResponse
): input is ScannerInputResponse & { inputType: "event"; input: EventType } {
  return input.input_type === "event";
}

export function isEventsInput(
  input: ScannerInputResponse
): input is ScannerInputResponse & { inputType: "events"; input: Event[] } {
  return input.input_type === "events";
}
