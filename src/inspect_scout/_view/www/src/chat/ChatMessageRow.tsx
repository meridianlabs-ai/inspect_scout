import clsx from "clsx";
import { FC, ReactNode } from "react";

import { ContentTool } from "../types";
import { ChatMessageTool } from "../types/log";

import { ChatMessage } from "./ChatMessage";
import styles from "./ChatMessageRow.module.css";
import { ResolvedMessage } from "./messages";
import { resolveToolInput } from "./tools/tool";
import { ToolCallView } from "./tools/ToolCallView";
import { ChatViewToolCallStyle } from "./types";

interface ChatMessageRowProps {
  index: number;
  parentName: string;
  labeled?: boolean;
  labels?: Record<string, string>;
  highlightLabeled?: boolean;
  resolvedMessage: ResolvedMessage;
  toolCallStyle: ChatViewToolCallStyle;
  indented?: boolean;
  padded?: boolean;
  highlightUserMessage?: boolean;
  allowLinking?: boolean;
}

/**
 * Renders the ChatMessage component.
 */
export const ChatMessageRow: FC<ChatMessageRowProps> = ({
  index,
  parentName,
  labeled,
  labels,
  highlightLabeled,
  resolvedMessage,
  toolCallStyle,
  indented,
  highlightUserMessage,
  allowLinking = true,
}) => {
  const views: ReactNode[] = [];
  const viewLabels: Array<string | undefined> = [];

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
  viewLabels.push(chatMessageLabel);

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
      const { input, description, functionCall, contentType } =
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
      viewLabels.push(toolLabel);
      if (toolCallStyle === "compact") {
        views.push(
          <ToolCallViewCompact idx={idx} functionCall={functionCall} />
        );
      } else {
        views.push(
          <ToolCallView
            id={`${index}-tool-call-${idx}`}
            key={`tool-call-${idx}`}
            functionCall={functionCall}
            input={input}
            description={description}
            contentType={contentType}
            output={resolvedToolOutput}
            collapsible={false}
          />
        );
      }
      idx++;
    }
  }

  if (labeled) {
    return (
      <>
        <div className={clsx(styles.grid)}>
          {views.map((view, idx) => {
            const label = viewLabels[idx];
            return (
              <>
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
              </>
            );
          })}
        </div>
      </>
    );
  } else {
    return (
      <div
        className={clsx(
          styles.container,
          styles.simple,
          highlightUserMessage && resolvedMessage.message.role === "user"
            ? styles.user
            : undefined
        )}
      >
        {views}
        {resolvedMessage.message.role === "user" ? (
          <div style={{ height: "10px" }}></div>
        ) : undefined}
      </div>
    );
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
