import clsx from "clsx";
import { FC } from "react";

import { ChatMessage } from "../../types/api-types";

import { ChatMessageRow } from "./ChatMessageRow";
import { resolveMessages } from "./messages";
import { ChatViewToolCallStyle } from "./types";

interface ChatViewProps {
  id?: string;
  messages: ChatMessage[];
  toolCallStyle?: ChatViewToolCallStyle;
  resolveToolCallsIntoPreviousMessage?: boolean;
  title?: string;
  indented?: boolean;
  className?: string | string[];
  allowLinking?: boolean;
  labels?: Record<string, string>;
  showLabels?: boolean;
  highlightLabeled?: boolean;
}

/**
 * Renders the ChatView component.
 */
export const ChatView: FC<ChatViewProps> = ({
  id,
  messages,
  toolCallStyle = "complete",
  resolveToolCallsIntoPreviousMessage = true,
  indented,
  labels,
  showLabels = true,
  highlightLabeled = false,
  className,
  allowLinking = true,
}) => {
  const collapsedMessages = resolveToolCallsIntoPreviousMessage
    ? resolveMessages(messages)
    : messages.map((msg) => {
        return {
          message: msg,
          toolMessages: [],
        };
      });
  const result = (
    <div className={clsx(className)}>
      {collapsedMessages.map((msg, index) => {
        return (
          <ChatMessageRow
            index={index}
            key={`${id}-msg-${index}`}
            parentName={id || "chat-view"}
            showLabels={showLabels}
            labels={labels}
            highlightLabeled={highlightLabeled}
            resolvedMessage={msg}
            indented={indented}
            toolCallStyle={toolCallStyle}
            allowLinking={allowLinking}
          />
        );
      })}
    </div>
  );
  return result;
};
