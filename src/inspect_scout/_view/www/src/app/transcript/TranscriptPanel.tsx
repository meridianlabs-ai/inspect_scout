import clsx from "clsx";
import { FC } from "react";

import { LoadingBar } from "../../components/LoadingBar";
import { useStore } from "../../state/store";
import { useRequiredParams } from "../../utils/router";
import { TranscriptsNavbar } from "../components/TranscriptsNavbar";
import { useServerTranscript, useServerTranscriptsDir } from "../server/hooks";

import styles from "./TranscriptPanel.module.css";

export const TranscriptPanel: FC = () => {
  const { transcriptId } = useRequiredParams("transcriptId");
  const transcriptsDir = useServerTranscriptsDir();
  const { loading, data: transcript } = useServerTranscript(
    transcriptsDir,
    transcriptId
  );

  const userTranscriptsDir = useStore((state) => state.userTranscriptsDir);
  const setUserTranscriptsDir = useStore(
    (state) => state.setUserTranscriptsDir
  );
  const resolvedTranscriptsDir = userTranscriptsDir || transcriptsDir;

  return (
    <div className={clsx(styles.container)}>
      <TranscriptsNavbar
        transcriptsDir={resolvedTranscriptsDir || ""}
        setTranscriptsDir={setUserTranscriptsDir}
      />
      <LoadingBar loading={loading} />
      {transcript && (
        <div>
          <h1>Transcript Detail</h1>
          <p>Transcript ID: {transcriptId}</p>
          {`${transcript.messages?.length} messages / ${transcript.events?.length} events`}
        </div>
      )}
    </div>
  );
};
