import clsx from "clsx";
import {
  forwardRef,
  useCallback,
  useImperativeHandle,
  useMemo,
  useRef,
} from "react";
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

export interface TranscriptViewNodesHandle {
  /** Scroll to an event by its ID. */
  scrollToEvent: (eventId: string) => void;
}

export const TranscriptViewNodes = forwardRef<
  TranscriptViewNodesHandle,
  TranscriptViewNodesProps
>(function TranscriptViewNodes(
  {
    id,
    eventNodes,
    defaultCollapsedIds,
    nodeFilter,
    scrollRef,
    initialEventId,
    offsetTop = 10,
    className,
  },
  ref
) {
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

  const scrollToEvent = useCallback(
    (eventId: string) => {
      const idx = flattenedNodes.findIndex((e) => e.id === eventId);
      if (idx !== -1 && listHandle.current) {
        listHandle.current.scrollToIndex({
          index: idx,
          align: "start",
          behavior: "auto",
          offset: offsetTop ? -offsetTop : undefined,
        });
      }
    },
    [flattenedNodes, offsetTop]
  );

  useImperativeHandle(ref, () => ({ scrollToEvent }), [scrollToEvent]);

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
});
