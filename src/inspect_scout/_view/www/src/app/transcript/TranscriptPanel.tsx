import clsx from "clsx";
import { FC } from "react";

import { LoadingBar } from "../../components/LoadingBar";
import { useStore } from "../../state/store";
import { TranscriptsNavbar } from "../components/TranscriptsNavbar";
import { useTranscriptRoute } from "../hooks";
import { useServerTranscriptsDir } from "../server/hooks";

import styles from "./TranscriptPanel.module.css";

export const TranscriptPanel: FC = () => {
  // Transcript data from route
  const { transcriptsDir: decodedTranscriptsDir, transcriptId } =
    useTranscriptRoute();

  // Server transcripts directory
  const { data: transcriptsDir, error, loading } = useServerTranscriptsDir();

  // User transcripts directory
  const userTranscriptsDir = useStore((state) => state.userTranscriptsDir);
  const setUserTranscriptsDir = useStore(
    (state) => state.setUserTranscriptsDir
  );
  const resolvedTranscriptsDir =
    decodedTranscriptsDir || userTranscriptsDir || transcriptsDir;

  return (
    <div className={clsx(styles.container)}>
      <TranscriptsNavbar
        transcriptsDir={resolvedTranscriptsDir || ""}
        setTranscriptsDir={setUserTranscriptsDir}
      />
      <LoadingBar loading={loading} />
      {!loading && !error && (
        <div>
          <h1>Transcript Detail</h1>
          <p>Transcript ID: {transcriptId}</p>
        </div>
      )}
    </div>
  );
};
