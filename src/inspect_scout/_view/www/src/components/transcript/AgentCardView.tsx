import clsx from "clsx";
import { FC, useCallback } from "react";

import { formatTokenCount } from "../../app/timeline/utils/swimlaneLayout";
import { formatDurationShort } from "../../utils/format";
import { ApplicationIcons } from "../icons";

import styles from "./AgentCardView.module.css";
import type { TimelineSpan } from "./timeline";
import { useTimelineSelect } from "./TimelineSelectContext";

interface AgentCardViewProps {
  span: TimelineSpan;
  className?: string | string[];
}

export const AgentCardView: FC<AgentCardViewProps> = ({ span, className }) => {
  const select = useTimelineSelect();

  const handleClick = useCallback(() => {
    select?.(span.id);
  }, [select, span.id]);

  const title = span.name.toLowerCase();
  const tokens = formatTokenCount(span.totalTokens);
  const duration = formatDurationShort(span.startTime, span.endTime);

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
    </div>
  );
};
