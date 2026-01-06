import {
  ContentCitation,
  ContentImage,
  ContentText,
  DocumentCitation,
  UrlCitation,
} from "../../types/api-types";

export type ChatViewToolCallStyle = "compact" | "complete" | "omit";

export type Citations = Array<
  ContentCitation | DocumentCitation | UrlCitation
> | null;
export type Citation = NonNullable<Citations>[number];

export interface ContentTool {
  type: "tool";
  content: (ContentImage | ContentText)[];
}
