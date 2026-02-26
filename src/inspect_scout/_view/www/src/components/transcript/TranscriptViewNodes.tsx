import clsx from "clsx";
import { FC, useMemo, useRef } from "react";
import { VirtuosoHandle } from "react-virtuoso";

import { useStore } from "../../state/store";

import styles from "./TranscriptViewNodes.module.css";
import { TranscriptVirtualList } from "./TranscriptVirtualList";
import { flatTree } from "./transform/flatten";
import { EventNode, EventType, kTranscriptCollapseScope } from "./types";

interface TranscriptViewNodesProps {
  id: string;
  eventNodes: EventNode[];
  defaultCollapsedIds: Record<string, boolean>;
  nodeFilter?: (node: EventNode<EventType>[]) => EventNode<EventType>[];
  scrollRef?: React.RefObject<HTMLDivElement | null>;
  initialEventId?: string | null;
  offsetTop?: number;
  className?: string | string[];
}

export const TranscriptViewNodes: FC<TranscriptViewNodesProps> = ({
  id,
  eventNodes,
  defaultCollapsedIds,
  nodeFilter,
  scrollRef,
  initialEventId,
  offsetTop = 10,
  className,
}) => {
  const listHandle = useRef<VirtuosoHandle | null>(null);

  // The list of events that have been collapsed
  const collapsedEvents = useStore((state) => state.transcriptCollapsedEvents);

  const flattenedNodes = useMemo(() => {
    // flattten the event tree
    return flatTree(
      nodeFilter ? nodeFilter(eventNodes) : eventNodes,
      (collapsedEvents
        ? collapsedEvents[kTranscriptCollapseScope]
        : undefined) || defaultCollapsedIds
    );
    // TODO: lint react-hooks/exhaustive-deps
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [eventNodes, collapsedEvents, defaultCollapsedIds]);

  return (
    <TranscriptVirtualList
      id={id}
      listHandle={listHandle}
      eventNodes={flattenedNodes}
      scrollRef={scrollRef}
      offsetTop={offsetTop}
      className={clsx(styles.listContainer, className)}
      initialEventId={initialEventId}
    />
  );
};
