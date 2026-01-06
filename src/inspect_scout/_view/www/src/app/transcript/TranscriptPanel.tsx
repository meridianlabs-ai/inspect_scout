import clsx from "clsx";
import { FC } from "react";

import { ErrorPanel } from "../../components/ErrorPanel";
import { LoadingBar } from "../../components/LoadingBar";
import { useStore } from "../../state/store";
import { useRequiredParams } from "../../utils/router";
import { TranscriptsNavbar } from "../components/TranscriptsNavbar";
import { useServerTranscriptsDir, useServerTranscript } from "../server/hooks";
import { useTranscriptDirParams } from "../utils/router";

import { TranscriptBody } from "./TranscriptBody";
import styles from "./TranscriptPanel.module.css";
import { TranscriptTitle } from "./TranscriptTitle";

export const TranscriptPanel: FC = () => {
  // Transcript data from route
  const { transcriptId } = useRequiredParams("transcriptId");
  const routeTranscriptsDir = useTranscriptDirParams();

  // Server transcripts directory
  const transcriptsDir = useServerTranscriptsDir();
  const {
    loading,
    data: transcript,
    error,
  } = useServerTranscript(transcriptsDir, transcriptId);

  // User transcripts directory
  const userTranscriptsDir = useStore((state) => state.userTranscriptsDir);
  const setUserTranscriptsDir = useStore(
    (state) => state.setUserTranscriptsDir
  );
  const resolvedTranscriptsDir =
    routeTranscriptsDir || userTranscriptsDir || transcriptsDir;

  return (
    <div className={clsx(styles.container)}>
      <TranscriptsNavbar
        transcriptsDir={resolvedTranscriptsDir || ""}
        setTranscriptsDir={setUserTranscriptsDir}
      />
      <LoadingBar loading={loading} />

      {!error && transcript && (
        <div className={styles.transcriptContainer}>
          <TranscriptTitle transcript={transcript} />
          <TranscriptBody transcript={transcript} />
        </div>
      )}
      {error && <ErrorPanel title="Error Loading Transcript" error={error} />}
    </div>
  );
};
