import { skipToken } from "@tanstack/react-query";
import clsx from "clsx";
import { FC, useRef } from "react";

import { ApiError } from "../../api/request";
import { ErrorPanel } from "../../components/ErrorPanel";
import { LoadingBar } from "../../components/LoadingBar";
import { useDocumentTitle } from "../../hooks/useDocumentTitle";
import { useStore } from "../../state/store";
import { useRequiredParams } from "../../utils/router";
import { TranscriptsNavbar } from "../components/TranscriptsNavbar";
import { useFilterConditions } from "../hooks/useFilterConditions";
import { useAdjacentTranscriptIds } from "../server/useAdjacentTranscriptIds";
import { useAppConfig } from "../server/useAppConfig";
import { useTranscript } from "../server/useTranscript";
import { TRANSCRIPTS_INFINITE_SCROLL_CONFIG } from "../transcripts/constants";
import { getTranscriptDisplayName } from "../utils/transcript";
import { useTranscriptsDir } from "../utils/useTranscriptsDir";

import { TranscriptBody } from "./TranscriptBody";
import { TranscriptNav } from "./TranscriptNav";
import styles from "./TranscriptPanel.module.css";
import { TranscriptTitle } from "./TranscriptTitle";

export const TranscriptPanel: FC = () => {
  // The core scroll element for the transcript panel
  const scrollRef = useRef<HTMLDivElement | null>(null);

  // Transcript data from route
  const { transcriptId } = useRequiredParams("transcriptId");

  // Transcripts directory (resolved from route, user preference, or config)
  const {
    displayTranscriptsDir,
    resolvedTranscriptsDir,
    resolvedTranscriptsDirSource,
    setTranscriptsDir,
  } = useTranscriptsDir(true);

  // Server transcripts directory
  const config = useAppConfig();
  const {
    loading,
    data: transcript,
    error,
  } = useTranscript(
    config.transcripts
      ? { location: config.transcripts.dir, id: transcriptId }
      : skipToken
  );
  const filter = Array.isArray(config.filter)
    ? config.filter.join(" ")
    : config.filter;

  // Set document title with transcript task name
  useDocumentTitle(getTranscriptDisplayName(transcript), "Transcripts");

  // Get sorting/filter from store
  const sorting = useStore((state) => state.transcriptsTableState.sorting);
  const condition = useFilterConditions();

  // Get adjacent transcript IDs
  const adjacentIds = useAdjacentTranscriptIds(
    transcriptId,
    resolvedTranscriptsDir,
    TRANSCRIPTS_INFINITE_SCROLL_CONFIG.pageSize,
    condition,
    sorting
  );
  const [prevId, nextId] = adjacentIds.data ?? [undefined, undefined];

  return (
    <div className={clsx(styles.container)}>
      <TranscriptsNavbar
        transcriptsDir={displayTranscriptsDir || ""}
        transcriptsDirSource={resolvedTranscriptsDirSource}
        filter={filter}
        setTranscriptsDir={setTranscriptsDir}
      >
        <TranscriptNav
          transcriptsDir={resolvedTranscriptsDir}
          transcript={transcript}
          nextId={nextId}
          prevId={prevId}
        />
      </TranscriptsNavbar>
      <LoadingBar loading={loading} />

      {!error && transcript && (
        <div className={styles.transcriptContainer} ref={scrollRef}>
          <TranscriptTitle transcript={transcript} />
          <TranscriptBody transcript={transcript} scrollRef={scrollRef} />
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
