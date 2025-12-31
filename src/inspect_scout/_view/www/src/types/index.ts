import { ContentImage, ContentText } from "./api-types";

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
