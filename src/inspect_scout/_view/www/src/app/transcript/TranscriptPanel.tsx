import clsx from "clsx";
import { FC } from "react";
import { useParams } from "react-router-dom";

import { useServerTranscript, useServerTranscriptsDir } from "../server/hooks";

import styles from "./TranscriptPanel.module.css";

export const TranscriptPanel: FC = () => {
  const { transcriptId } = useParams<{ transcriptId: string }>();
  const transcriptsDir = useServerTranscriptsDir().data;
  const { loading, data: transcript } = useServerTranscript(
    transcriptsDir,
    transcriptId
  );

  return (
    <div className={clsx(styles.container)}>
      <h1>Transcript Detail</h1>
      <p>Transcript ID: {transcriptId}</p>
      {loading
        ? "loading"
        : `${transcript?.messages?.length} messages / ${transcript?.events?.length} events`}
    </div>
  );
};
