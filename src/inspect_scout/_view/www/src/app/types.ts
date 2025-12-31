import { EventType } from "../transcript/types";
import { Transcript } from "../types";
import {
  ModelUsage,
  JsonValue,
  ChatMessageSystem,
  ChatMessageUser,
  ChatMessageAssistant,
  ChatMessageTool,
  Event,
  ChatMessage,
} from "../types/api-types";

export interface ScanResultInputData {
  input: Input;
  inputType: InputType;
}

export type Input =
  | Transcript
  | ChatMessage[]
  | Event[]
  | MessageType
  | EventType;

export type InputType =
  | "transcript"
  | "message"
  | "messages"
  | "event"
  | "events";

export interface ScanResultSummary {
  // Basic Info
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
  validationTarget: boolean | Record<string, boolean>;

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
  | "scanjobs"
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
  input: ScanResultInputData
): input is ScanResultInputData & {
  inputType: "transcript";
  input: Transcript;
} {
  return input.inputType === "transcript";
}

export function isMessageInput(
  input: ScanResultInputData
): input is ScanResultInputData & { inputType: "message"; input: MessageType } {
  return input.inputType === "message";
}

export function isMessagesInput(
  input: ScanResultInputData
): input is ScanResultInputData & {
  inputType: "messages";
  input: ChatMessage[];
} {
  return input.inputType === "messages";
}

export function isEventInput(
  input: ScanResultInputData
): input is ScanResultInputData & { inputType: "event"; input: EventType } {
  return input.inputType === "event";
}

export function isEventsInput(
  input: ScanResultInputData
): input is ScanResultInputData & { inputType: "events"; input: Event[] } {
  return input.inputType === "events";
}
