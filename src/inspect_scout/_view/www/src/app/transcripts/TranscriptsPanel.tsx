import clsx from "clsx";
import { FC } from "react";

import { ErrorPanel } from "../../components/ErrorPanel";
import { LoadingBar } from "../../components/LoadingBar";
import { NoContentsPanel } from "../../components/NoContentsPanel";
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
  const userTranscriptsDir = useStore((state) => state.userTranscriptsDir);

  const setUserTranscriptsDir = useStore(
    (state) => state.setUserTranscriptsDir
  );
  const resolvedTranscriptDir = userTranscriptsDir || transcriptDir;

  const {
    data: transcripts,
    error,
    loading,
  } = useServerTranscripts(resolvedTranscriptDir);
  const hasError = errorDir || error;
  const hasTranscripts = transcripts && transcripts.length > 0;

  return (
    <div className={clsx(styles.container)}>
      <TranscriptsNavbar
        bordered={true}
        transcriptDir={resolvedTranscriptDir}
        setTranscriptDir={setUserTranscriptsDir}
      />
      <LoadingBar loading={loading || loadingDir} />
      {hasError && (
        <ErrorPanel
          title="Error Loading Transcript"
          error={{
            message: errorDir?.message || error?.message || "Unknown Error",
          }}
        />
      )}
      {!hasError && hasTranscripts && (
        <TranscriptsGrid transcripts={transcripts} />
      )}
      {!hasError && !hasTranscripts ? (
        <NoContentsPanel text="No transcripts found." />
      ) : null}
      <Footer
        itemCount={transcripts?.length || 0}
        id={"transcripts-footer"}
        paginated={false}
      />
    </div>
  );
};
