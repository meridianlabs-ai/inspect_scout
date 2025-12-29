import clsx from "clsx";
import { FC } from "react";
import { useParams } from "react-router-dom";

import { LoadingBar } from "../../components/LoadingBar";
import { useStore } from "../../state/store";
import { Transcript } from "../../types/api-types";
import { AsyncData, loading } from "../../utils/asyncData";
import { TranscriptsNavbar } from "../components/TranscriptsNavbar";
import { useServerTranscript, useServerTranscriptsDir } from "../server/hooks";

import styles from "./TranscriptPanel.module.css";

export const TranscriptPanel: FC = () => {
  const { transcriptId } = useParams<{ transcriptId: string }>();
  const { data: transcriptsDir, error } = useServerTranscriptsDir();
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
      {!loading && !error && (
        <div>
          <h1>Transcript Detail</h1>
          <p>Transcript ID: {transcriptId}</p>
          {loading
            ? "loading"
            : `${transcript?.messages?.length} messages / ${transcript?.events?.length} events`}
        </div>
      )}
    </div>
  );
};

const useTheStuff = (
  transcriptId: string | undefined
): AsyncData<{
  transcriptDir: string;
  transcript: Transcript;
}> => {
  const { data: transcriptsDir, error } = useServerTranscriptsDir();
  const { loading, data: transcript } = useServerTranscript(
    transcriptsDir,
    transcriptId
  );
  return loading;
};
