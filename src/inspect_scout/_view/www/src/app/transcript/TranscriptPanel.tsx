import clsx from "clsx";
import { FC } from "react";

import { ApiError } from "../../api/request";
import { ErrorPanel } from "../../components/ErrorPanel";
import { LoadingBar } from "../../components/LoadingBar";
import { useStore } from "../../state/store";
import { useRequiredParams } from "../../utils/router";
import { TranscriptsNavbar } from "../components/TranscriptsNavbar";
import { appTranscriptsDir, useConfig } from "../server/useConfig";
import { useServerTranscript } from "../server/useServerTranscript";
import { useTranscriptDirParams } from "../utils/router";

import { TranscriptBody } from "./TranscriptBody";
import styles from "./TranscriptPanel.module.css";
import { TranscriptTitle } from "./TranscriptTitle";

export const TranscriptPanel: FC = () => {
  // Transcript data from route
  const { transcriptId } = useRequiredParams("transcriptId");
  const routeTranscriptsDir = useTranscriptDirParams();

  // Server transcripts directory
  const config = useConfig();
  const transcriptsDir = appTranscriptsDir(config);
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
      {error && (
        <ErrorPanel
          title={
            error instanceof ApiError && error.status === 413
              ? "Transcript Too Large"
              : "Error Loading Transcript"
          }
          error={
            error instanceof ApiError && error.status === 413
              ? { message: "This transcript exceeds the maximum size limit." }
              : error
          }
        />
      )}
    </div>
  );
};
