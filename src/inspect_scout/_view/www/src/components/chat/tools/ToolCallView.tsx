import clsx from "clsx";
import { FC, useMemo } from "react";

import {
  ContentAudio,
  ContentData,
  ContentImage,
  ContentReasoning,
  ContentText,
  ContentVideo,
  ToolCallContent,
} from "../../../types/api-types";
import ExpandablePanel from "../../ExpandablePanel";
import { MarkdownDiv } from "../../MarkdownDiv";
import { MessageContent } from "../MessageContent";
import { defaultContext, MessagesContext } from "../MessageContents";
import { ContentTool } from "../types";

import { getCustomToolView } from "./customToolRendering";
import styles from "./ToolCallView.module.css";
import { ToolInput } from "./ToolInput";
import { ToolTitle } from "./ToolTitle";

export interface ToolCallViewProps {
  id: string;
  tool: string;
  functionCall: string;
  input?: unknown;
  description?: string;
  contentType?: string;
  view?: ToolCallContent;
  output:
    | string
    | number
    | boolean
    | ContentText
    | ContentAudio
    | ContentImage
    | ContentVideo
    | ContentTool
    | ContentReasoning
    | ContentData
    | (
        | ContentText
        | ContentAudio
        | ContentImage
        | ContentVideo
        | ContentTool
        | ContentReasoning
        | ContentData
      )[];
  mode?: "compact";
  collapsible?: boolean;
}

/**
 * Renders the ToolCallView component.
 */
export const ToolCallView: FC<ToolCallViewProps> = ({
  id,
  tool,
  functionCall,
  input,
  description,
  contentType,
  view,
  output,
  mode,
  collapsible = true,
}) => {
  // don't collapse if output includes an image
  function isContentImage(
    value:
      | string
      | number
      | boolean
      | ContentText
      | ContentAudio
      | ContentImage
      | ContentVideo
      | ContentTool
      | ContentReasoning
      | ContentData
  ) {
    if (value && typeof value === "object") {
      if (value.type === "image") {
        return true;
      } else if (value.type === "tool") {
        if (
          Array.isArray(value.content) &&
          value.content.some(isContentImage)
        ) {
          return true;
        }
      }
    }
    return false;
  }

  const collapse = Array.isArray(output)
    ? output.every((item) => !isContentImage(item))
    : !isContentImage(output);
  const normalizedContent = useMemo(() => normalizeContent(output), [output]);

  const hasContent = normalizedContent.find((c) => {
    if (c.type === "tool") {
      for (const t of c.content) {
        if (t.type === "text") {
          if (t.text) {
            return true;
          }
        } else {
          return true;
        }
      }
      return false;
    } else {
      return true;
    }
  });

  // See if there is a custom view for this tool
  const customToolView = getCustomToolView({
    id,
    tool,
    functionCall,
    input,
    description,
    contentType,
    output,
  });
  if (customToolView) {
    return customToolView;
  }

  const contents = mode !== "compact" ? input : input || functionCall;
  const context = defaultContext();
  return (
    <div className={clsx(styles.toolCallView)}>
      <div>
        {mode !== "compact" && (!view || view.title) ? (
          <ToolTitle
            title={view?.title || functionCall}
            description={description}
          />
        ) : (
          ""
        )}
        <ExpandablePanel
          id={`${id}-tool-input`}
          collapse={true}
          border={false}
          lines={20}
          className={clsx("text-size-small")}
        >
          <ToolInput
            contentType={contentType}
            contents={contents}
            toolCallView={view}
          />
        </ExpandablePanel>
      </div>
      {contentType === "markdown" && hasContent ? (
        <ExpandablePanel
          id={`${id}-tool-content`}
          collapse={collapse}
          border={true}
          lines={15}
          className={clsx("text-size-small")}
        >
          <MarkdownToolOutput
            contents={normalizedContent}
            context={context}
          />
        </ExpandablePanel>
      ) : hasContent && collapsible ? (
        <ExpandablePanel
          id={`${id}-tool-content`}
          collapse={collapse}
          border={true}
          lines={15}
          className={clsx("text-size-small")}
        >
          <MessageContent contents={normalizedContent} context={context} />
        </ExpandablePanel>
      ) : (
        <MessageContent contents={normalizedContent} context={context} />
      )}
    </div>
  );
};

/**
 * Renders the ToolCallView component.
 */
type NormalizedContentItem =
  | ContentText
  | ContentImage
  | ContentAudio
  | ContentVideo
  | ContentTool
  | ContentReasoning
  | ContentData;

/**
 * Renders tool output with text as markdown, passing non-text content
 * (e.g. images) through MessageContent for normal rendering.
 */
const MarkdownToolOutput: FC<{
  contents: NormalizedContentItem[];
  context: MessagesContext;
}> = ({ contents, context }) => {
  // Flatten tool wrapper to get inner content items
  const items = contents.flatMap((c) =>
    c.type === "tool" ? c.content : [c]
  );

  return (
    <>
      {items.map((item, i) => {
        if (item.type === "text" && item.text) {
          return <MarkdownDiv key={`md-${i}`} markdown={item.text} />;
        }
        return (
          <MessageContent
            key={`content-${i}`}
            contents={[item] as NormalizedContentItem[]}
            context={context}
          />
        );
      })}
    </>
  );
};

const normalizeContent = (
  output:
    | string
    | number
    | boolean
    | ContentText
    | ContentImage
    | ContentAudio
    | ContentVideo
    | ContentTool
    | ContentReasoning
    | ContentData
    | (
        | ContentText
        | ContentImage
        | ContentAudio
        | ContentVideo
        | ContentTool
        | ContentReasoning
        | ContentData
      )[]
): (
  | ContentText
  | ContentImage
  | ContentAudio
  | ContentVideo
  | ContentTool
  | ContentReasoning
  | ContentData
)[] => {
  if (Array.isArray(output)) {
    return output;
  } else {
    return [
      {
        type: "tool",
        content: [
          {
            type: "text",
            text: String(output),
            refusal: null,
            internal: null,
            citations: null,
          },
        ],
      },
    ];
  }
};
