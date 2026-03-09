import clsx from "clsx";
import {
  forwardRef,
  useCallback,
  useEffect,
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
  /** Scroll to a flattened-list index. */
  scrollToIndex: (index: number) => void;
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

  const scrollToIndex = useCallback(
    (index: number) => {
      listHandle.current?.scrollToIndex({
        index,
        align: "start",
        behavior: "auto",
        offset: offsetTop ? -offsetTop : undefined,
      });
    },
    [offsetTop]
  );

  useImperativeHandle(ref, () => ({ scrollToEvent, scrollToIndex }), [
    scrollToEvent,
    scrollToIndex,
  ]);

  // Cmd/Ctrl+Arrow keyboard shortcuts to jump to top/bottom of the event list.
  // Uses a two-stage scroll for ArrowDown: first jump near the end so Virtuoso
  // measures those items, then scroll to the very last item after a short delay.
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.metaKey || event.ctrlKey) {
        if (event.key === "ArrowUp") {
          listHandle.current?.scrollToIndex({ index: 0, align: "center" });
          event.preventDefault();
        } else if (event.key === "ArrowDown") {
          listHandle.current?.scrollToIndex({
            index: Math.max(flattenedNodes.length - 5, 0),
            align: "center",
          });

          // Allow Virtuoso to measure the near-bottom items before
          // scrolling to the true last item.
          setTimeout(() => {
            listHandle.current?.scrollToIndex({
              index: flattenedNodes.length - 1,
              align: "end",
            });
          }, 250);
          event.preventDefault();
        }
      }
    };

    const scrollElement = scrollRef?.current;
    if (scrollElement) {
      scrollElement.addEventListener("keydown", handleKeyDown);
      if (!scrollElement.hasAttribute("tabIndex")) {
        scrollElement.setAttribute("tabIndex", "0");
      }

      return () => {
        scrollElement.removeEventListener("keydown", handleKeyDown);
      };
    }
  }, [scrollRef, flattenedNodes, listHandle]);

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
