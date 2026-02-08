import clsx from "clsx";
import { FC, useMemo } from "react";

import { ApprovalEvent, ModelEvent, ToolEvent } from "../../types/api-types";
import { ChatView } from "../chat/ChatView";
import { resolveToolInput } from "../chat/tools/tool";
import { ToolCallView } from "../chat/tools/ToolCallView";
import { ApplicationIcons } from "../icons";
import { PulsingDots } from "../PulsingDots";

import { ApprovalEventView } from "./ApprovalEventView";
import { EventPanel } from "./event/EventPanel";
import { formatTiming, formatTitle } from "./event/utils";
import styles from "./ToolEventView.module.css";
import { EventNode, EventType } from "./types";

interface ToolEventViewProps {
  eventNode: EventNode<ToolEvent>;
  children: EventNode<EventType>[];
  className?: string | string[];
}

/**
 * Renders the ToolEventView component.
 */
export const ToolEventView: FC<ToolEventViewProps> = ({
  eventNode,
  children,
  className,
}) => {
  const event = eventNode.event;

  // Extract tool input
  const { name, input, description, functionCall, contentType } = useMemo(
    () => resolveToolInput(event.function, event.arguments),
    [event.function, event.arguments]
  );

  const { approvalNode, lastModelNode } = useMemo(() => {
    const approvalNode = children.find((e) => {
      return e.event.event === "approval";
    });

    // Find a model message to render, if there is one

    const lastModelNode = children.findLast((e) => {
      return e.event.event === "model";
    });

    return {
      approvalNode: approvalNode as EventNode<ApprovalEvent> | undefined,
      lastModelNode: lastModelNode as EventNode<ModelEvent> | undefined,
    };
    // TODO: lint react-hooks/exhaustive-deps
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [event.events]);

  const title = `Tool: ${event.view?.title || event.function}`;
  return (
    <EventPanel
      eventNodeId={eventNode.id}
      depth={eventNode.depth}
      title={formatTitle(title, undefined, event.working_time)}
      className={className}
      subTitle={
        event.timestamp
          ? formatTiming(event.timestamp, event.working_start)
          : undefined
      }
      icon={ApplicationIcons.solvers.use_tools}
      childIds={children.map((child) => child.id)}
      collapseControl="bottom"
    >
      <div data-name="Summary" className={styles.summary}>
        <ToolCallView
          id={`${eventNode.id}-tool-call`}
          tool={name}
          functionCall={functionCall}
          input={input}
          description={description}
          contentType={contentType}
          output={event.error?.message || event.result || ""}
          mode="compact"
          view={event.view ? event.view : undefined}
        />

        {lastModelNode ? (
          <ChatView
            id={`${eventNode.id}-toolcall-chatmessage`}
            messages={lastModelNode.event.output.choices.map((m) => m.message)}
            toolCallStyle="compact"
            allowLinking={false}
          />
        ) : undefined}

        {approvalNode ? (
          <ApprovalEventView
            eventNode={approvalNode}
            className={styles.approval}
          />
        ) : (
          ""
        )}
        {event.pending ? (
          <div className={clsx(styles.progress)}>
            <PulsingDots subtle={false} size="medium" />
          </div>
        ) : undefined}
      </div>
    </EventPanel>
  );
};
