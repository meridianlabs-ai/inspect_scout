import { FC } from "react";

import {
  ChatMessageAssistant,
  ChatMessageSystem,
  ChatMessageTool,
  ChatMessageUser,
} from "../../types/api-types";

import { MessageContent } from "./MessageContent";
import { Citation } from "./types";

interface MessageContentsProps {
  message:
    | ChatMessageAssistant
    | ChatMessageSystem
    | ChatMessageUser
    | ChatMessageTool;
}

export interface MessagesContext {
  citations: Citation[];
}

export const defaultContext = () => {
  return {
    citeOffset: 0,
    citations: [],
  };
};

export const MessageContents: FC<MessageContentsProps> = ({ message }) => {
  const context: MessagesContext = defaultContext();
  return (
    <>
      {message.content && (
        <MessageContent contents={message.content} context={context} />
      )}
    </>
  );
};
