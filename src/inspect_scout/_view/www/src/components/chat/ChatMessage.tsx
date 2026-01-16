import clsx from "clsx";
import { FC, memo, useState } from "react";

import { useTranscriptNavigation } from "../../app/transcript/hooks/useTranscriptNavigation";
import { isHostedEnvironment } from "../../router/url";
import {
  ChatMessageAssistant,
  ChatMessageSystem,
  ChatMessageTool,
  ChatMessageUser,
} from "../../types/api-types";
import { RecordTree } from "../content/RecordTree";
import { CopyButton } from "../CopyButton";
import ExpandablePanel from "../ExpandablePanel";
import { ApplicationIcons } from "../icons";
import { LabeledValue } from "../LabeledValue";

import styles from "./ChatMessage.module.css";
import { MessageContents } from "./MessageContents";
import { ChatViewToolCallStyle } from "./types";

interface ChatMessageProps {
  id: string;
  message:
    | ChatMessageAssistant
    | ChatMessageSystem
    | ChatMessageUser
    | ChatMessageTool;
  toolMessages: ChatMessageTool[];
  indented?: boolean;
  toolCallStyle: ChatViewToolCallStyle;
  allowLinking?: boolean;
}

export const ChatMessage: FC<ChatMessageProps> = memo(
  ({ id, message, indented, allowLinking = true }) => {
    // Generate full URL for deep linking to this message
    const { getFullMessageUrl } = useTranscriptNavigation();
    const messageUrl = isHostedEnvironment()
      ? getFullMessageUrl(message.id || "")
      : undefined;

    const collapse = message.role === "system" || message.role === "user";

    const [mouseOver, setMouseOver] = useState(false);

    return (
      <div
        className={clsx(
          message.role,
          "text-size-base",
          styles.message,
          message.role === "system" ? styles.systemRole : undefined,
          message.role === "user" ? styles.userRole : undefined,
          mouseOver ? styles.hover : undefined
        )}
        onMouseEnter={() => setMouseOver(true)}
        onMouseLeave={() => setMouseOver(false)}
      >
        <div
          className={clsx(
            styles.messageGrid,
            message.role === "tool" ? styles.toolMessageGrid : undefined,
            "text-style-label"
          )}
        >
          {message.role}
          {message.role === "tool" ? `: ${message.function}` : ""}
          {messageUrl && allowLinking ? (
            <CopyButton
              icon={ApplicationIcons.link}
              value={messageUrl}
              className={clsx(styles.copyLink)}
            />
          ) : (
            ""
          )}
        </div>
        <div
          className={clsx(
            styles.messageContents,
            indented ? styles.indented : undefined
          )}
        >
          <ExpandablePanel
            id={`${id}-message`}
            collapse={collapse}
            lines={collapse ? 15 : 25}
          >
            <MessageContents key={`${id}-contents`} message={message} />
          </ExpandablePanel>

          {message.metadata && Object.keys(message.metadata).length > 0 ? (
            <LabeledValue
              label="Metadata"
              className={clsx(styles.metadataLabel, "text-size-smaller")}
            >
              <RecordTree
                record={message.metadata}
                id={`${id}-metadata`}
                defaultExpandLevel={0}
              />
            </LabeledValue>
          ) : (
            ""
          )}
        </div>
      </div>
    );
  }
);
