import clsx from "clsx";
import { FC } from "react";

import { ErrorPanel } from "../../components/ErrorPanel";
import { LoadingBar } from "../../components/LoadingBar";
import { Condition, SimpleCondition } from "../../query/types";
import { useStore } from "../../state/store";
import { TranscriptInfo } from "../../types";
import { Footer } from "../components/Footer";
import { TranscriptsNavbar } from "../components/TranscriptsNavbar";
import { useServerTranscripts, useServerTranscriptsDir } from "../server/hooks";

import { TranscriptsGrid } from "./TranscriptsGrid";
import styles from "./TranscriptsPanel.module.css";

export const TranscriptsPanel: FC = () => {
  // Resolve the active transcripts directory
  const transcriptDir = useServerTranscriptsDir();
  const userTranscriptsDir = useStore((state) => state.userTranscriptsDir);
  const setUserTranscriptsDir = useStore(
    (state) => state.setUserTranscriptsDir
  );
  const resolvedTranscriptDir = userTranscriptsDir || transcriptDir;

  // Filtering
  const columnFilters =
    useStore((state) => state.transcriptsTableState.columnFilters) ?? {};
  const filterConditions = Object.values(columnFilters).filter(
    (filter): filter is SimpleCondition => Boolean(filter)
  );

  // Sorting
  const condition = filterConditions.reduce<Condition | undefined>(
    (acc, condition) => (acc ? acc.and(condition) : condition),
    undefined
  );
  const sorting = useStore((state) => state.transcriptsTableState.sorting);

  const {
    data: transcriptsResponse,
    error,
    loading,
  } = useServerTranscripts(resolvedTranscriptDir, condition, sorting);
  const transcripts = (transcriptsResponse?.items ?? []) as TranscriptInfo[];

  return (
    <div className={clsx(styles.container)}>
      <TranscriptsNavbar
        bordered={true}
        transcriptsDir={resolvedTranscriptDir}
        setTranscriptsDir={setUserTranscriptsDir}
      />
      <LoadingBar loading={loading} />
      {error && (
        <ErrorPanel
          title="Error Loading Transcript"
          error={{
            message: error.message || "Unknown Error",
          }}
        />
      )}
      {!error && (
        <TranscriptsGrid
          transcripts={transcripts}
          transcriptsDir={resolvedTranscriptDir}
        />
      )}
      <Footer
        id={"transcripts-footer"}
        itemCount={transcripts?.length || 0}
        paginated={false}
      />
    </div>
  );
};
