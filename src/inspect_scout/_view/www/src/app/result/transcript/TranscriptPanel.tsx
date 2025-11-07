import clsx from "clsx";
import { FC, useRef } from "react";

import { TranscriptView } from "../../../transcript/TranscriptView";
import { EventNode, EventType } from "../../../transcript/types";
import { ScannerData } from "../../types";

import styles from "./TranscriptPanel.module.css";

interface TranscriptPanelProps {
  id: string;
  result?: ScannerData;
  nodeFilter?: (node: EventNode<EventType>[]) => EventNode<EventType>[];
}

export const TranscriptPanel: FC<TranscriptPanelProps> = ({
  id,
  result,
  nodeFilter,
}) => {
  const scrollRef = useRef<HTMLDivElement | null>(null);

  return (
    <div ref={scrollRef} className={clsx(styles.container)}>
      <TranscriptView
        id={id}
        events={result.scanEvents || []}
        scrollRef={scrollRef}
        nodeFilter={nodeFilter}
      />
    </div>
  );
};
