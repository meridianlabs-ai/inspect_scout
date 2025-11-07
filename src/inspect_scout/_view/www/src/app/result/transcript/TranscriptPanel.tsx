import clsx from "clsx";
import { FC, useRef } from "react";

import { TranscriptView } from "../../../transcript/TranscriptView";
import { ScannerData } from "../../types";

import styles from "./TranscriptPanel.module.css";

interface TranscriptPanelProps {
  id: string;
  result?: ScannerData;
}

export const TranscriptPanel: FC<TranscriptPanelProps> = ({ id, result }) => {
  const scrollRef = useRef<HTMLDivElement | null>(null);

  return (
    <div ref={scrollRef} className={clsx(styles.container)}>
      <TranscriptView
        id={id}
        events={result.scanEvents || []}
        scrollRef={scrollRef}
      />
    </div>
  );
};
