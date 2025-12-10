import { EventType } from "../transcript/types";
import { ModelUsage, Transcript } from "../types";
import {
  JsonValue,
  ChatMessageSystem,
  ChatMessageUser,
  ChatMessageAssistant,
  ChatMessageTool,
  Events,
} from "../types/log";

export interface SortColumn {
  column: string;
  direction: "asc" | "desc";
}

export type ErrorScope = "scanjobs" | "scanner" | "dataframe";

export type ResultGroup = "source" | "label" | "id" | "epoch" | "none";

export type ValueType =
  | "boolean"
  | "number"
  | "string"
  | "array"
  | "object"
  | "null";

export interface ScannerCore {
  uuid?: string;
  inputType: "transcript" | "message" | "messages" | "event" | "events";
  explanation?: string;
  label?: string;
  eventReferences: ScannerReference[];
  messageReferences: ScannerReference[];
  validationResult: boolean | Record<string, boolean>;
  validationTarget: boolean | Record<string, boolean>;
  value: string | boolean | number | null | unknown[] | object;
  valueType: ValueType;
  transcriptMetadata: Record<string, JsonValue>;
  transcriptSourceId: string;
  scanError?: string;
  scanErrorRefusal?: boolean;
}

export interface ScannerReference {
  type: "message" | "event";
  id: string;
  cite?: string;
}

export type MessageType =
  | ChatMessageSystem
  | ChatMessageUser
  | ChatMessageAssistant
  | ChatMessageTool;

// Base interface with common properties
export interface ScannerData extends ScannerCore {
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
}

// Type guard functions for value types
export function isStringValue(
  result: ScannerCore
): result is ScannerCore & { valueType: "string"; value: string } {
  return result.valueType === "string";
}

export function isNumberValue(
  result: ScannerCore
): result is ScannerCore & { valueType: "number"; value: number } {
  return result.valueType === "number";
}

export function isBooleanValue(
  result: ScannerCore
): result is ScannerCore & { valueType: "boolean"; value: boolean } {
  return result.valueType === "boolean";
}

export function isNullValue(
  result: ScannerCore
): result is ScannerCore & { valueType: "null"; value: null } {
  return result.valueType === "null";
}

export function isArrayValue(
  result: ScannerCore
): result is ScannerCore & { valueType: "array"; value: unknown[] } {
  return result.valueType === "array";
}

export function isObjectValue(
  result: ScannerCore
): result is ScannerCore & { valueType: "object"; value: object } {
  return result.valueType === "object";
}
