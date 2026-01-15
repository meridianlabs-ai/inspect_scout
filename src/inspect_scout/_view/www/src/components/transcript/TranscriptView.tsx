import { FC } from "react";

import { Event } from "../../types/api-types";

import { useEventNodes } from "./hooks/useEventNodes";
import { TranscriptViewNodes } from "./TranscriptViewNodes";
import { EventNode, EventType } from "./types";

interface TranscriptViewProps {
  id: string;
  events?: Event[];
  nodeFilter?: (node: EventNode<EventType>[]) => EventNode<EventType>[];
  scrollRef?: React.RefObject<HTMLDivElement | null>;
  initialEventId?: string | null;
  className?: string | string[];
}

export const TranscriptView: FC<TranscriptViewProps> = ({
  id,
  events,
  nodeFilter,
  scrollRef,
  initialEventId,
  className,
}) => {
  // The list of events that have been collapsed
  const { eventNodes, defaultCollapsedIds } = useEventNodes(
    events || [],
    false
  );

  return (
    <TranscriptViewNodes
      id={id}
      eventNodes={eventNodes}
      defaultCollapsedIds={defaultCollapsedIds}
      nodeFilter={nodeFilter}
      scrollRef={scrollRef}
      initialEventId={initialEventId}
      className={className}
    />
  );
};
