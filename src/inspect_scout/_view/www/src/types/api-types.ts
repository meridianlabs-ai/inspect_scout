// Re-export API types from generated OpenAPI schema
import type { components } from "./generated";

export type Status = components["schemas"]["Status"];
export type ScanSpec = components["schemas"]["ScanSpec"];
export type Summary = components["schemas"]["Summary"];
export type Error = components["schemas"]["Error"];
export type ScannerSpec = components["schemas"]["ScannerSpec"];
export type ScannerSummary = components["schemas"]["ScannerSummary"];
export type ModelUsage = components["schemas"]["ModelUsage"];
export type ModelConfig = components["schemas"]["ModelConfig"];
export type TranscriptsResponse = components["schemas"]["TranscriptsResponse"];
