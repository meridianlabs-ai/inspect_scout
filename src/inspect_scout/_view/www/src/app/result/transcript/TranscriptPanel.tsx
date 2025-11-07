import clsx from "clsx";
import { FC, useMemo, useRef } from "react";
import { VirtuosoHandle } from "react-virtuoso";

import { useCollapsedState } from "../../../state/hooks";
import { useStore } from "../../../state/store";
import { TranscriptVirtualList } from "../../../transcript/TranscriptVirtualList";
import { flatTree } from "../../../transcript/transform/flatten";
import { useEventNodes } from "../../../transcript/transform/hooks";
import { kTranscriptCollapseScope } from "../../../transcript/types";
import { ScannerData } from "../../types";

import styles from "./TranscriptPanel.module.css";

interface TranscriptPanelProps {
  id: string;
  result?: ScannerData;
}

export const TranscriptPanel: FC<TranscriptPanelProps> = ({ id, result }) => {
  const events = result?.scanEvents || [];
  const listHandle = useRef<VirtuosoHandle | null>(null);

  // Collapse state
  // The list of events that have been collapsed
  const collapsedEvents = useStore((state) => state.transcriptCollapsedEvents);
  const [collapsed] = useCollapsedState(
    `transcript-panel-${id || "na"}`,
    false
  );

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

  const scrollRef = useRef<HTMLDivElement | null>(null);

  return (
    <div
      ref={scrollRef}
      className={clsx(
        styles.container,
        collapsed ? styles.collapsed : undefined
      )}
    >
      <TranscriptVirtualList
        id={id}
        listHandle={listHandle}
        eventNodes={flattenedNodes}
        scrollRef={scrollRef}
        offsetTop={10}
        className={styles.listContainer}
        initialEventId={undefined}
      />
    </div>
  );
};
