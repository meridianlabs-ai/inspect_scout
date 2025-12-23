import { EventType } from "../transcript/types";
import { ModelUsage, Transcript, ScanResultInputData } from "../types";
import {
  JsonValue,
  ChatMessageSystem,
  ChatMessageUser,
  ChatMessageAssistant,
  ChatMessageTool,
  Events,
  Messages,
} from "../types/log";

// Derive Input and InputType from the generated ScanResultInputData discriminated union
export type Input = ScanResultInputData["input"];
export type InputType = ScanResultInputData["input_type"];

export interface ScanResultSummary {
  // Basic Info
  uuid?: string;
  explanation?: string;
  label?: string;
  timestamp?: Date;

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
  scanEvents: Events;
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

  transcriptDate?: Date;
  transcriptAgent?: string;
  transcriptAgentArgs?: Record<string, unknown>;
  transcriptScore?: JsonValue;
  transcriptSuccess?: boolean;
  transcriptTotalTime?: number;
  transcroptTotalTokens?: number;
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
  input_type: "transcript";
  input: Transcript;
} {
  return input.input_type === "transcript";
}

export function isMessageInput(
  input: ScanResultInputData
): input is ScanResultInputData & {
  input_type: "message";
  input: MessageType;
} {
  return input.input_type === "message";
}

export function isMessagesInput(
  input: ScanResultInputData
): input is ScanResultInputData & { input_type: "messages"; input: Messages } {
  return input.input_type === "messages";
}

export function isEventInput(
  input: ScanResultInputData
): input is ScanResultInputData & { input_type: "event"; input: EventType } {
  return input.input_type === "event";
}

export function isEventsInput(
  input: ScanResultInputData
): input is ScanResultInputData & { input_type: "events"; input: Events } {
  return input.input_type === "events";
}
