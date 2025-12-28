import clsx from "clsx";
import { FC } from "react";
import { useParams } from "react-router-dom";

import { LoadingBar } from "../../components/LoadingBar";
import { useStore } from "../../state/store";
import { TranscriptsNavbar } from "../components/TranscriptsNavbar";
import { useServerTranscriptsDir } from "../server/hooks";

import styles from "./TranscriptPanel.module.css";

export const TranscriptPanel: FC = () => {
  const { transcriptId } = useParams<{ transcriptId: string }>();
  const { data: transcriptsDir, error, loading } = useServerTranscriptsDir();

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
      {!loading && !error && (
        <div>
          <h1>Transcript Detail</h1>
          <p>Transcript ID: {transcriptId}</p>
        </div>
      )}
    </div>
  );
};
