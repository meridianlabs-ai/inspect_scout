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
  className,
  allowLinking = true,
  messageLabels,
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
        const number =
          collapsedMessages.length > 1 && labeled ? index + 1 : undefined;

        const msgLabel =
          messageLabels && msg.message.id ? messageLabels[msg.message.id] : "";
        const label = msgLabel || number;

        return (
          <ChatMessageRow
            key={`${id}-msg-${index}`}
            parentName={id || "chat-view"}
            label={label ? String(label) : undefined}
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
