import clsx from "clsx";
import { FC } from "react";

import { ApiError } from "../../api/request";
import { ErrorPanel } from "../../components/ErrorPanel";
import { LoadingBar } from "../../components/LoadingBar";
import { useStore } from "../../state/store";
import { useRequiredParams } from "../../utils/router";
import { TranscriptsNavbar } from "../components/TranscriptsNavbar";
import { useFilterConditions } from "../hooks/useFilterConditions";
import { useAdjacentTranscriptIds } from "../server/useAdjacentTranscriptIds";
import { appAliasedPath, useConfig } from "../server/useConfig";
import { useServerTranscript } from "../server/useServerTranscript";
import { TRANSCRIPTS_INFINITE_SCROLL_CONFIG } from "../transcripts/constants";
import { useTranscriptDirParams } from "../utils/router";

import { TranscriptBody } from "./TranscriptBody";
import { TranscriptNav } from "./TranscriptNav";
import styles from "./TranscriptPanel.module.css";
import { TranscriptTitle } from "./TranscriptTitle";

export const TranscriptPanel: FC = () => {
  // Transcript data from route
  const { transcriptId } = useRequiredParams("transcriptId");
  const routeTranscriptsDir = useTranscriptDirParams();

  // Server transcripts directory
  const config = useConfig();
  const {
    loading,
    data: transcript,
    error,
  } = useServerTranscript(config.transcripts_dir, transcriptId);

  // User transcripts directory
  const userTranscriptsDir = useStore((state) => state.userTranscriptsDir);
  const setUserTranscriptsDir = useStore(
    (state) => state.setUserTranscriptsDir
  );
  const transcriptsDir =
    routeTranscriptsDir || userTranscriptsDir || config.transcripts_dir || "";
  const displayTranscriptsDir = appAliasedPath(config, transcriptsDir || null);

  // Get sorting/filter from store
  const sorting = useStore((state) => state.transcriptsTableState.sorting);
  const condition = useFilterConditions();

  // Get adjacent transcript IDs
  const adjacentIds = useAdjacentTranscriptIds(
    transcriptId,
    transcriptsDir,
    TRANSCRIPTS_INFINITE_SCROLL_CONFIG.pageSize,
    condition,
    sorting
  );
  const [prevId, nextId] = adjacentIds.data ?? [undefined, undefined];

  return (
    <div className={clsx(styles.container)}>
      <TranscriptsNavbar
        transcriptsDir={displayTranscriptsDir || ""}
        setTranscriptsDir={setUserTranscriptsDir}
      >
        <TranscriptNav
          transcriptsDir={transcriptsDir}
          transcript={transcript}
          nextId={nextId}
          prevId={prevId}
        />
      </TranscriptsNavbar>
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
