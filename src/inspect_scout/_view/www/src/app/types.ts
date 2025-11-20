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

export type ErrorScope = "scanjobs" | "scanner" | "dataframe";

export type ScannerCore =
  | ScannerCoreTranscript
  | ScannerCoreMessage
  | ScannerCoreMessages
  | ScannerCoreEvent
  | ScannerCoreEvents;

export type ValueType =
  | "boolean"
  | "number"
  | "string"
  | "array"
  | "object"
  | "null";

export interface ScannerCoreBase {
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

interface ScannerCoreTranscript extends ScannerCoreBase {
  inputType: "transcript";
  input: Transcript;
}

interface ScannerCoreMessage extends ScannerCoreBase {
  inputType: "message";
  input: MessageType;
}

interface ScannerCoreMessages extends ScannerCoreBase {
  inputType: "messages";
  input: MessageType[];
}

interface ScannerCoreEvent extends ScannerCoreBase {
  inputType: "event";
  input: EventType;
}

interface ScannerCoreEvents extends ScannerCoreBase {
  inputType: "events";
  input: EventType[];
}

export type ScannerData =
  | ScannerDataTranscript
  | ScannerDataMessage
  | ScannerDataMessages
  | ScannerDataEvent
  | ScannerDataEvents;

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
interface ScannerDataBase extends ScannerCoreBase {
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

interface ScannerDataTranscript extends ScannerDataBase {
  inputType: "transcript";
  input: Transcript;
}

interface ScannerDataMessage extends ScannerDataBase {
  inputType: "message";
  input: MessageType;
}

interface ScannerDataMessages extends ScannerDataBase {
  inputType: "messages";
  input: MessageType[];
}

interface ScannerDataEvent extends ScannerDataBase {
  inputType: "event";
  input: EventType;
}

interface ScannerDataEvents extends ScannerDataBase {
  inputType: "events";
  input: EventType[];
}

export function isTranscriptData(
  data: ScannerData
): data is ScannerDataTranscript {
  return data.inputType === "transcript";
}

export function isMessageData(data: ScannerData): data is ScannerDataMessage {
  return data.inputType === "message";
}

export function isMessagesData(data: ScannerData): data is ScannerDataMessages {
  return data.inputType === "messages";
}

export function isEventData(data: ScannerData): data is ScannerDataEvent {
  return data.inputType === "event";
}

export function isEventsData(data: ScannerData): data is ScannerDataEvents {
  return data.inputType === "events";
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
