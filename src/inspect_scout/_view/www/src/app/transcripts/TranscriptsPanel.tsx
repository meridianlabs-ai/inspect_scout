import clsx from "clsx";
import { FC } from "react";

import { ErrorPanel } from "../../components/ErrorPanel";
import { LoadingBar } from "../../components/LoadingBar";
import { useStore } from "../../state/store";
import { Footer } from "../components/Footer";
import { TranscriptsNavbar } from "../components/TranscriptsNavbar";
import { useServerTranscripts, useServerTranscriptsDir } from "../server/hooks";

import { TranscriptsGrid } from "./TranscriptsGrid";
import styles from "./TranscriptsPanel.module.css";

export const TranscriptsPanel: FC = () => {
  const {
    data: transcriptDir,
    error: errorDir,
    loading: loadingDir,
  } = useServerTranscriptsDir();
  const transcriptsDatabasePath = useStore(
    (state) => state.transcriptsDatabasePath
  );
  const setTranscriptsDatabasePath = useStore(
    (state) => state.setTranscriptsDatabasePath
  );

  const {
    data: transcripts,
    error,
    loading,
  } = useServerTranscripts(transcriptsDatabasePath || transcriptDir);

  return (
    <div className={clsx(styles.container)}>
      <TranscriptsNavbar
        bordered={true}
        transcriptDir={transcriptsDatabasePath || transcriptDir}
        setTranscriptDir={setTranscriptsDatabasePath}
      />
      <LoadingBar loading={!!loading || !!loadingDir} />
      {(errorDir || error) && (
        <ErrorPanel
          title="Error Loading Transcript"
          error={{
            message: errorDir?.message || error?.message || "Unknown Error",
          }}
        />
      )}
      {!error && <TranscriptsGrid transcripts={transcripts} />}
      <Footer
        itemCount={transcripts?.length || 0}
        id={"transcripts-footer"}
        paginated={false}
      />
    </div>
  );
};
