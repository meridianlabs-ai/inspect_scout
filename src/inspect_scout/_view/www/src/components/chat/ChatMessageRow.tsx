import clsx from "clsx";
import { FC, Fragment, ReactNode } from "react";

import { ChatMessageTool } from "../../types/api-types";

import { ChatMessage } from "./ChatMessage";
import styles from "./ChatMessageRow.module.css";
import { ResolvedMessage } from "./messages";
import { resolveToolInput } from "./tools/tool";
import { ToolCallView } from "./tools/ToolCallView";
import { ChatViewToolCallStyle, ContentTool } from "./types";

interface ChatMessageRowProps {
  index: number;
  parentName: string;
  labels?: Record<string, string>;
  showLabels?: boolean;
  highlightLabeled?: boolean;
  resolvedMessage: ResolvedMessage;
  toolCallStyle: ChatViewToolCallStyle;
  indented?: boolean;
  padded?: boolean;
  highlightUserMessage?: boolean;
  allowLinking?: boolean;
  className?: string | string[];
}

/**
 * Renders the ChatMessage component.
 */
export const ChatMessageRow: FC<ChatMessageRowProps> = ({
  index,
  parentName,
  showLabels,
  labels,
  highlightLabeled,
  resolvedMessage,
  toolCallStyle,
  indented,
  highlightUserMessage,
  allowLinking = true,
  className,
}) => {
  const views: ReactNode[] = [];
  const viewLabels: Array<string | undefined> = [];
  const useLabels = showLabels || Object.keys(labels || {}).length > 0;

  if (useLabels) {
    // The chat message and label
    const number = index + 1;
    // TODO: don't do this for every row
    const maxlabelLen = labels
      ? Object.values(labels).reduce((curr, r) => {
          return Math.max(r.length, curr);
        }, 0)
      : 3;
    const chatMessageLabel =
      labels && resolvedMessage.message.id
        ? labels[resolvedMessage.message.id] || "\u00A0".repeat(maxlabelLen * 2)
        : String(number) || undefined;
    viewLabels.push(chatMessageLabel);
  }

  // The chat message
  views.push(
    <ChatMessage
      id={`${parentName}-chat-messages`}
      message={resolvedMessage.message}
      toolMessages={resolvedMessage.toolMessages}
      indented={indented}
      toolCallStyle={toolCallStyle}
      allowLinking={allowLinking}
    />
  );

  // The tool messages associated with this chat message
  if (
    toolCallStyle !== "omit" &&
    resolvedMessage.message.role === "assistant" &&
    resolvedMessage.message.tool_calls &&
    resolvedMessage.message.tool_calls.length
  ) {
    const toolMessages = resolvedMessage.toolMessages || [];
    let idx = 0;
    for (const tool_call of resolvedMessage.message.tool_calls) {
      // Extract tool input
      const { name, input, description, functionCall, contentType } =
        resolveToolInput(tool_call.function, tool_call.arguments);

      let toolMessage: ChatMessageTool | undefined;
      if (tool_call.id) {
        toolMessage = toolMessages.find((msg) => {
          return msg.tool_call_id === tool_call.id;
        });
      } else {
        toolMessage = toolMessages[idx];
      }

      // The label (if any)
      const toolLabel = labels?.[toolMessage?.id || ""] || undefined;

      // Resolve the tool output
      const resolvedToolOutput = resolveToolMessage(toolMessage);
      if (useLabels) {
        viewLabels.push(toolLabel);
      }

      if (toolCallStyle === "compact") {
        views.push(
          <ToolCallViewCompact idx={idx} functionCall={functionCall} />
        );
      } else {
        views.push(
          <ToolCallView
            id={`${index}-tool-call-${idx}`}
            key={`tool-call-${idx}`}
            tool={name}
            functionCall={functionCall}
            input={input}
            description={description}
            contentType={contentType}
            output={resolvedToolOutput}
            view={tool_call.view ?? undefined}
          />
        );
      }
      idx++;
    }
  }

  if (useLabels) {
    return (
      <>
        <div className={clsx(styles.grid, className)}>
          {views.map((view, idx) => {
            const label = viewLabels[idx];
            return (
              <Fragment key={`chat-message-row-${index}-part-${idx}`}>
                <div
                  className={clsx(
                    "text-size-smaller",
                    "text-style-secondary",
                    styles.number,
                    styles.label
                  )}
                >
                  {label}
                </div>
                <div
                  className={clsx(
                    styles.container,
                    highlightUserMessage &&
                      resolvedMessage.message.role === "user"
                      ? styles.user
                      : undefined,
                    idx === 0 ? styles.first : undefined,
                    idx === views.length - 1 ? styles.last : undefined,
                    highlightLabeled && label?.trim()
                      ? styles.highlight
                      : undefined
                  )}
                >
                  {view}
                </div>
              </Fragment>
            );
          })}
        </div>
      </>
    );
  } else {
    return views.map((view, idx) => {
      return (
        <div
          key={`chat-message-row-unlabeled-${index}-part-${idx}`}
          className={clsx(
            styles.container,
            idx === 0 ? styles.first : undefined,
            idx === views.length - 1 ? styles.last : undefined,
            idx === views.length - 1 ? styles.bottomMargin : undefined,
            className,
            styles.simple,
            highlightUserMessage && resolvedMessage.message.role === "user"
              ? styles.user
              : undefined
          )}
        >
          {view}
        </div>
      );
    });
  }
};

const resolveToolMessage = (toolMessage?: ChatMessageTool): ContentTool[] => {
  if (!toolMessage) {
    return [];
  }

  const content =
    toolMessage.error !== null && toolMessage.error
      ? toolMessage.error.message
      : toolMessage.content;
  if (typeof content === "string") {
    return [
      {
        type: "tool",
        content: [
          {
            type: "text",
            text: content,
            refusal: null,
            internal: null,
            citations: null,
          },
        ],
      },
    ];
  } else {
    const result = content
      .map((con) => {
        if (typeof con === "string") {
          return {
            type: "tool",
            content: [
              {
                type: "text",
                text: con,
                refusal: null,
                internal: null,
                citations: null,
              },
            ],
          } as ContentTool;
        } else if (con.type === "text") {
          return {
            content: [con],
            type: "tool",
          } as ContentTool;
        } else if (con.type === "image") {
          return {
            content: [con],
            type: "tool",
          } as ContentTool;
        }
      })
      .filter((con) => con !== undefined);
    return result;
  }
};

const ToolCallViewCompact: FC<{
  idx: number;
  functionCall: string;
}> = ({ idx, functionCall }) => {
  return (
    <div key={`tool-call-${idx}`}>
      <code className={clsx(styles.codeCompact)}>tool: {functionCall}</code>
    </div>
  );
};
