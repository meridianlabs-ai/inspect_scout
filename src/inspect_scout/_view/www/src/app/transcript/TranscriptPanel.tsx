import clsx from "clsx";
import { FC } from "react";
import { useParams } from "react-router-dom";

import { LoadingBar } from "../../components/LoadingBar";
import { useStore } from "../../state/store";
import { TranscriptNavbar } from "../components/TranscriptNavBar";
import { useServerTranscriptsDir } from "../server/hooks";

import styles from "./TranscriptPanel.module.css";

export const TranscriptPanel: FC = () => {
  const { transcriptId } = useParams<{ transcriptId: string }>();
  const { data: transcriptsDir, error, loading } = useServerTranscriptsDir();

  const transcriptsDatabasePath = useStore(
    (state) => state.transcriptsDatabasePath
  );

  return (
    <div className={clsx(styles.container)}>
      <TranscriptNavbar
        transcriptsDir={transcriptsDatabasePath || transcriptsDir}
        bordered={true}
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
