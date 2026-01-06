import clsx from "clsx";
import { FC, useRef } from "react";

import { TranscriptView } from "../../../components/transcript/TranscriptView";
import { EventNode, EventType } from "../../../components/transcript/types";
import { ScanResultData } from "../../types";

import styles from "./TranscriptPanel.module.css";

interface TranscriptPanelProps {
  id: string;
  resultData?: ScanResultData;
  nodeFilter?: (node: EventNode<EventType>[]) => EventNode<EventType>[];
}

export const TranscriptPanel: FC<TranscriptPanelProps> = ({
  id,
  resultData,
  nodeFilter,
}) => {
  const scrollRef = useRef<HTMLDivElement | null>(null);

  return (
    <div ref={scrollRef} className={clsx(styles.container)}>
      <TranscriptView
        id={id}
        events={resultData?.scanEvents || []}
        scrollRef={scrollRef}
        nodeFilter={nodeFilter}
      />
    </div>
  );
};
