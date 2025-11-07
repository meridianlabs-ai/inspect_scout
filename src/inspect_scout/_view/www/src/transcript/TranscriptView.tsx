import { FC, useMemo, useRef } from "react";
import { VirtuosoHandle } from "react-virtuoso";

import { useStore } from "../state/store";
import { Events } from "../types/log";

import styles from "./TranscriptView.module.css";
import { TranscriptVirtualList } from "./TranscriptVirtualList";
import { flatTree } from "./transform/flatten";
import { useEventNodes } from "./transform/hooks";
import { kTranscriptCollapseScope } from "./types";

interface TranscriptViewProps {
  id: string;
  events?: Events;
  scrollRef?: React.RefObject<HTMLDivElement | null>;
}

export const TranscriptView: FC<TranscriptViewProps> = ({
  id,
  events,
  scrollRef,
}) => {
  const listHandle = useRef<VirtuosoHandle | null>(null);

  // The list of events that have been collapsed
  const collapsedEvents = useStore((state) => state.transcriptCollapsedEvents);
  const { eventNodes, defaultCollapsedIds } = useEventNodes(events, false);

  const flattenedNodes = useMemo(() => {
    // flattten the event tree
    return flatTree(
      eventNodes,
      (collapsedEvents
        ? collapsedEvents[kTranscriptCollapseScope]
        : undefined) || defaultCollapsedIds
    );
  }, [eventNodes, collapsedEvents, defaultCollapsedIds]);

  return (
    <TranscriptVirtualList
      id={id}
      listHandle={listHandle}
      eventNodes={flattenedNodes}
      scrollRef={scrollRef}
      offsetTop={10}
      className={styles.listContainer}
      initialEventId={undefined}
    />
  );
};
