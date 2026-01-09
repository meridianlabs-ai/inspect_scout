// Re-export API types from generated OpenAPI schema
import type { components } from "./generated";

export type ActiveScanInfo = components["schemas"]["ActiveScanInfo"];
export type ActiveScansResponse = components["schemas"]["ActiveScansResponse"];
export type Status = components["schemas"]["Status"];
export type ScanSpec = components["schemas"]["ScanSpec"];
export type Summary = components["schemas"]["Summary"];
export type Error = components["schemas"]["Error"];
export type ScannerSpec = components["schemas"]["ScannerSpec"];
export type ScannerSummary = components["schemas"]["ScannerSummary"];
export type ModelUsage = components["schemas"]["ModelUsage"];
export type ModelConfig = components["schemas"]["ModelConfig"];
export type TranscriptsResponse = components["schemas"]["TranscriptsResponse"];
export type Transcript = components["schemas"]["Transcript"];
export type Pagination = components["schemas"]["Pagination"];
export type TranscriptInfo = components["schemas"]["TranscriptInfo"];
export type ScansResponse = components["schemas"]["ScansResponse"];
export type AppConfig = components["schemas"]["AppConfig"];
export type ApprovalEvent = components["schemas"]["ApprovalEvent"];
export type ErrorEvent = components["schemas"]["ErrorEvent"];
export type InfoEvent = components["schemas"]["InfoEvent"];
export type InputEvent = components["schemas"]["InputEvent"];
export type LoggerEvent = components["schemas"]["LoggerEvent"];
export type ModelEvent = components["schemas"]["ModelEvent"];
export type SampleInitEvent = components["schemas"]["SampleInitEvent"];
export type SampleLimitEvent = components["schemas"]["SampleLimitEvent"];
export type SandboxEvent = components["schemas"]["SandboxEvent"];
export type ScoreEvent = components["schemas"]["ScoreEvent"];
export type ScoreEditEvent = components["schemas"]["ScoreEditEvent"];
export type SpanBeginEvent = components["schemas"]["SpanBeginEvent"];
export type SpanEndEvent = components["schemas"]["SpanEndEvent"];
export type StateEvent = components["schemas"]["StateEvent"];
export type StepEvent = components["schemas"]["StepEvent"];
export type StoreEvent = components["schemas"]["StoreEvent"];
export type SubtaskEvent = components["schemas"]["SubtaskEvent"];
export type ToolEvent = components["schemas"]["ToolEvent"];
export type Event = components["schemas"]["Event"];

export type JsonChange = components["schemas"]["JsonChange"];

export type ChatMessage = components["schemas"]["ChatMessage"];
export type ChatMessageAssistant =
  components["schemas"]["ChatMessageAssistant"];
export type ChatMessageSystem = components["schemas"]["ChatMessageSystem"];
export type ChatMessageTool = components["schemas"]["ChatMessageTool"];
export type ChatMessageUser = components["schemas"]["ChatMessageUser"];

export type ModelCall = components["schemas"]["ModelCall"];

export type ToolInfo = components["schemas"]["ToolInfo"];
export type ToolCallContent = components["schemas"]["ToolCallContent"];
export type ToolCallView = components["schemas"]["ToolCallView"];

export type ContentAudio = components["schemas"]["ContentAudio"];
export type ContentData = components["schemas"]["ContentData"];
export type ContentDocument = components["schemas"]["ContentDocument"];
export type ContentImage = components["schemas"]["ContentImage"];
export type ContentReasoning = components["schemas"]["ContentReasoning"];
export type ContentText = components["schemas"]["ContentText"];
export type ContentToolUse = components["schemas"]["ContentToolUse"];
export type ContentVideo = components["schemas"]["ContentVideo"];
export type CodeResponse = components["schemas"]["CodeResponse"];

export type Score = components["schemas"]["Score"];

export type ContentCitation = components["schemas"]["ContentCitation"];
export type DocumentCitation = components["schemas"]["DocumentCitation"];
export type UrlCitation = components["schemas"]["UrlCitation"];

// TODO: Events have timestamp as optional (because value isn't required but they use a factory to always have a value). Consider the distinction between input and output types.
// TODO: ContentDocument type mime_type optional?

// TODO: app/types.ts
// This type is unknown in TS, but could probably be narrower
export type JsonValue = components["schemas"]["JsonValue"];

// TODO: Sample Event Limit (Literal that doesn't have a type alias)
// Literals that don't have type aliases aren't being exported.
// TODO: Emit properly in _api_v2 for literals
export type Type17 =
  | "message"
  | "time"
  | "working"
  | "token"
  | "operator"
  | "custom";

// TODO: ??
export type JsonChangeOp =
  | "remove"
  | "add"
  | "replace"
  | "move"
  | "test"
  | "copy";

// TODO: Format1, Format2, MessageContent.tsx
export type Format1 = "wav" | "mp3";
export type Format2 = "mp4" | "mpeg" | "mov";

// TODO: ModelEventView
// This blows up generation because of the Union of a literal and a type
export type ToolChoice = ("auto" | "any" | "none") | ToolFunction;

export interface ToolFunction {
  name: string;
}
