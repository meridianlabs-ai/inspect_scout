import clsx from "clsx";
import { FC } from "react";

import { Messages } from "../types/log";

import { ChatMessageRow } from "./ChatMessageRow";
import { resolveMessages } from "./messages";
import { ChatViewToolCallStyle } from "./types";

interface ChatViewProps {
  id?: string;
  messages: Messages;
  toolCallStyle?: ChatViewToolCallStyle;
  resolveToolCallsIntoPreviousMessage?: boolean;
  title?: string;
  indented?: boolean;
  labeled?: boolean;
  highlightLabeled?: boolean;
  className?: string | string[];
  allowLinking?: boolean;
  messageLabels?: Record<string, string>;
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
  labeled = true,
  messageLabels,
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
            labeled={labeled}
            labels={messageLabels}
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
