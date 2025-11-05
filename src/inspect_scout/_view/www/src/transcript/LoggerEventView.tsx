import clsx from "clsx";
import { LoggerEvent } from "../types/log";
import { ApplicationIcons } from "../app/appearance/icons";
import { EventRow } from "./event/EventRow";

import { FC } from "react";
import { parsedJson as maybeParseJson } from "../utils/json";
import { MetaDataGrid } from "../content/MetaDataGrid";
import styles from "./LoggerEventView.module.css";
import { EventNode } from "./types";
import { App } from "../App";

interface LoggerEventViewProps {
  eventNode: EventNode<LoggerEvent>;
  className?: string | string[];
}

/**
 * Renders the LoggerEventView component.
 */
export const LoggerEventView: FC<LoggerEventViewProps> = ({
  eventNode,
  className,
}) => {
  const event = eventNode.event;
  const obj = maybeParseJson(event.message.message);
  return (
    <EventRow
      className={className}
      title={event.message.level}
      icon={
        ApplicationIcons.logging[event.message.level.toLowerCase()] ||
        ApplicationIcons.info
      }
    >
      <div className={clsx("text-size-base", styles.grid)}>
        <div className={clsx("text-size-smaller")}>
          {obj !== undefined && obj !== null ? (
            <MetaDataGrid entries={obj as Record<string, unknown>} />
          ) : (
            event.message.message
          )}
        </div>
        <div className={clsx("text-size-smaller", "text-style-secondary")}>
          {event.message.filename}:{event.message.lineno}
        </div>
      </div>
    </EventRow>
  );
};
