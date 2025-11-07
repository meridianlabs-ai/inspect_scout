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

export interface ScannerCore {
  uuid?: string;
  inputType: "transcript" | "message" | "messages" | "event" | "events";
  explanation?: string;
  validationResult: boolean | Record<string, boolean>;
  validationTarget: boolean | Record<string, boolean>;
  value: string | boolean | number | null | unknown[] | object;
  valueType: "string" | "number" | "boolean" | "null" | "array" | "object";
  transcriptMetadata: Record<string, JsonValue>;
  transcriptSourceId: string;
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
  cite: string;
}

export type MessageType =
  | ChatMessageSystem
  | ChatMessageUser
  | ChatMessageAssistant
  | ChatMessageTool;

// Base interface with common properties
interface ScannerDataBase extends ScannerCore {
  answer?: string;
  eventReferences: ScannerReference[];
  inputIds: string[];
  messageReferences: ScannerReference[];
  metadata: Record<string, JsonValue>;
  scanError?: string;
  scanErrorTraceback?: string;
  scanEvents: Events;
  scanId: string;
  scanMetdata: Record<string, JsonValue>;
  scanModelUsage: Record<string, ModelUsage>;
  scanTags: string[];
  scanTotalTokens: number;
  scannerFile: string;
  scannerKey: string;
  scannerName: string;
  scannerParams: Record<string, JsonValue>;
  timestamp: Date;
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
