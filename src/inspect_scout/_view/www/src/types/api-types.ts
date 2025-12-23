// Re-export API types from generated OpenAPI schema
import type { components, operations } from "./generated";

export type Status = components["schemas"]["Status"];
export type ScanSpec = components["schemas"]["ScanSpec"];
export type Summary = components["schemas"]["Summary"];
export type Error = components["schemas"]["Error"];
export type ScannerSpec = components["schemas"]["ScannerSpec"];
export type ScannerSummary = components["schemas"]["ScannerSummary"];
export type ModelUsage = components["schemas"]["ModelUsage"];
export type ModelConfig = components["schemas"]["ModelConfig"];

// Scanner input discriminated union variants
export type TranscriptInput = components["schemas"]["TranscriptInput"];
export type MessageInput = components["schemas"]["MessageInput"];
export type MessagesInput = components["schemas"]["MessagesInput"];
export type EventInput = components["schemas"]["EventInput"];
export type EventsInput = components["schemas"]["EventsInput"];

// Scanner input discriminated union (from operation response type)
export type ScanResultInputData =
  operations["scanner_input_scans__scan___scanner___uuid__input_get"]["responses"][200]["content"]["application/json"];
