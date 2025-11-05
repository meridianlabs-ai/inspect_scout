import { ChatMessage, ChatMessages } from "../types";

export const lastAssistantMessage = (
  messages: ChatMessages
): ChatMessage | undefined => {
  for (let i = messages.length - 1; i >= 0; i--) {
    if (messages[i]?.role === "assistant") {
      return messages[i];
    }
  }
  return undefined;
};

export const firstUserMessage = (
  messages: ChatMessages
): ChatMessage | undefined => {
  for (let i = 0; i < messages.length; i++) {
    if (messages[i]?.role === "user") {
      return messages[i];
    }
  }
  return undefined;
};
