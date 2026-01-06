import { FC } from "react";

import { ApplicationIcons } from "../../app/appearance/icons";
import { ErrorEvent } from "../../types/api-types";
import { formatDateTime } from "../../utils/format";
import { ANSIDisplay } from "../AnsiDisplay";

import { EventPanel } from "./event/EventPanel";
import { EventNode } from "./types";

interface ErrorEventViewProps {
  eventNode: EventNode<ErrorEvent>;
  className?: string | string[];
}

/**
 * Renders the ErrorEventView component.
 */
export const ErrorEventView: FC<ErrorEventViewProps> = ({
  eventNode,
  className,
}) => {
  const event = eventNode.event;
  return (
    <EventPanel
      eventNodeId={eventNode.id}
      depth={eventNode.depth}
      title="Error"
      className={className}
      subTitle={
        event.timestamp ? formatDateTime(new Date(event.timestamp)) : undefined
      }
      icon={ApplicationIcons.error}
    >
      <ANSIDisplay
        output={event.error.traceback_ansi}
        style={{
          fontSize: "clamp(0.3rem, 1.1vw, 0.8rem)",
          margin: "0.5em 0",
        }}
      />
    </EventPanel>
  );
};
