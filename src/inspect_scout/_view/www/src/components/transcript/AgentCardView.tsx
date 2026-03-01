import clsx from "clsx";
import { FC, useCallback } from "react";

import { formatTokenCount } from "../../app/timeline/utils/swimlaneLayout";
import type { ToolEvent } from "../../types/api-types";
import { formatDurationShort } from "../../utils/format";
import { isMessageContent, MessageContent } from "../chat/MessageContent";
import { defaultContext } from "../chat/MessageContents";
import ExpandablePanel from "../ExpandablePanel";
import { ApplicationIcons } from "../icons";

import styles from "./AgentCardView.module.css";
import type { TimelineSpan } from "./timeline";
import { useTimelineSelect } from "./TimelineSelectContext";

interface AgentCardViewProps {
  span: TimelineSpan;
  toolEvent?: ToolEvent;
  className?: string | string[];
}

export const AgentCardView: FC<AgentCardViewProps> = ({
  span,
  toolEvent,
  className,
}) => {
  const select = useTimelineSelect();

  const handleClick = useCallback(() => {
    select?.(span.id);
  }, [select, span.id]);

  const title = span.name.toLowerCase();
  const tokens = formatTokenCount(span.totalTokens);
  const duration = formatDurationShort(span.startTime, span.endTime);

  const resultContent = toolEvent ? normalizeResult(toolEvent.result) : null;

  return (
    <div className={clsx(styles.card, className)} onClick={handleClick}>
      <div className={clsx(styles.header, "text-size-small")}>
        <i
          className={clsx(
            ApplicationIcons.agent,
            styles.icon,
            "text-style-secondary"
          )}
        />
        <div
          className={clsx(
            styles.title,
            "text-style-secondary",
            "text-style-label"
          )}
        >
          sub-agent: {title}
        </div>
        <div />
        <div className={clsx(styles.meta, "text-style-secondary")}>
          {tokens} &middot; {duration}
        </div>
        <i
          className={clsx(
            ApplicationIcons.chevron.right,
            styles.disclosure,
            "text-style-secondary"
          )}
        />
      </div>
      {span.description && (
        <div className={clsx(styles.description, "text-size-small")}>
          {span.description}
        </div>
      )}
      {resultContent && resultContent.length > 0 && (
        <div
          className={styles.result}
          onClick={(e) => e.stopPropagation()}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") e.stopPropagation();
          }}
        >
          <ExpandablePanel
            id={`agent-result-${span.id}`}
            collapse={true}
            border={true}
            lines={20}
            className={clsx("text-size-small")}
          >
            <MessageContent
              contents={resultContent}
              context={defaultContext()}
            />
          </ExpandablePanel>
        </div>
      )}
    </div>
  );
};

function normalizeResult(
  result: ToolEvent["result"]
): Parameters<typeof MessageContent>[0]["contents"] {
  if (Array.isArray(result)) {
    return result.filter(isMessageContent);
  }
  if (typeof result === "object" && result !== null && "type" in result) {
    return [result];
  }
  return [
    {
      type: "text" as const,
      text: String(result),
      refusal: null,
      internal: null,
      citations: null,
    },
  ];
}
