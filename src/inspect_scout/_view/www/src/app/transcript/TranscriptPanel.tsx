import clsx from "clsx";
import { FC } from "react";
import { useParams } from "react-router-dom";

import styles from "./TranscriptPanel.module.css";

export const TranscriptPanel: FC = () => {
  const { transcriptId } = useParams<{ transcriptId: string }>();

  return (
    <div className={clsx(styles.container)}>
      <h1>Transcript Detail</h1>
      <p>Transcript ID: {transcriptId}</p>
    </div>
  );
};
