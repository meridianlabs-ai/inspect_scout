import { ContentImage, ContentText } from "./api-types";

// Scout types generated from OpenAPI schema
// To regenerate: .venv/bin/python scripts/export_openapi_schema.py
export type {
  Status,
  ScanSpec,
  Summary,
  Error,
  ScannerSpec as Scanner,
  ScannerSummary,
  ModelConfig as Model,
} from "./api-types";

// Query builder
export {
  transcriptColumns,
  Column,
  ConditionBuilder,
  TranscriptColumns,
} from "../query";

export type { ConditionModel, ScalarValue } from "../query";

export interface ContentTool {
  type: "tool";
  content: (ContentImage | ContentText)[];
}
