import { skipToken } from "@tanstack/react-query";
import clsx from "clsx";
import { FC, useCallback, useEffect, useMemo } from "react";

import { ErrorPanel } from "../../components/ErrorPanel";
import { LoadingBar } from "../../components/LoadingBar";
import { useStore } from "../../state/store";
import { TranscriptInfo } from "../../types/api-types";
import { Footer } from "../components/Footer";
import { TranscriptsNavbar } from "../components/TranscriptsNavbar";
import { useTranscriptsFilterBarProps } from "../hooks/useTranscriptsFilterBarProps";
import { useAppConfig } from "../server/useAppConfig";
import { useServerTranscriptsInfinite } from "../server/useServerTranscriptsInfinite";
import { useTranscriptsDir } from "../utils/useTranscriptsDir";

import { TRANSCRIPTS_INFINITE_SCROLL_CONFIG } from "./constants";
import { TranscriptFilterBar } from "./TranscriptFilterBar";
import { TranscriptsGrid } from "./TranscriptsGrid";
import styles from "./TranscriptsPanel.module.css";

export const TranscriptsPanel: FC = () => {
  // Resolve the active transcripts directory
  const {
    displayTranscriptsDir,
    resolvedTranscriptsDir,
    resolvedTranscriptsDirSource,
    setTranscriptsDir,
  } = useTranscriptsDir();
  const config = useAppConfig();
  const filter = Array.isArray(config.filter)
    ? config.filter.join(" ")
    : config.filter;

  const sorting = useStore((state) => state.transcriptsTableState.sorting);

  // Clear detail state
  const clearTranscriptState = useStore((state) => state.clearTranscriptState);
  useEffect(() => {
    clearTranscriptState();
  }, [clearTranscriptState]);

  const {
    filterCodeValues,
    filterSuggestions,
    onFilterColumnChange,
    condition,
  } = useTranscriptsFilterBarProps(resolvedTranscriptsDir);
  const { data, error, fetchNextPage, hasNextPage, isFetching } =
    useServerTranscriptsInfinite(
      resolvedTranscriptsDir
        ? {
            location: resolvedTranscriptsDir,
            pageSize: TRANSCRIPTS_INFINITE_SCROLL_CONFIG.pageSize,
            filter: condition,
            sorting,
          }
        : skipToken
    );

  const transcripts: TranscriptInfo[] = useMemo(
    () => data?.pages.flatMap((page) => page.items) ?? [],
    [data]
  );

  const handleScrollNearEnd = useCallback(
    (distanceFromBottom: number) => {
      if (distanceFromBottom <= 0) {
        console.log("Hit bottom!");
      }
      fetchNextPage({ cancelRefetch: false }).catch(console.error);
    },
    [fetchNextPage]
  );

  return (
    <div className={clsx(styles.container)}>
      <TranscriptsNavbar
        bordered={true}
        transcriptsDir={displayTranscriptsDir}
        transcriptsDirSource={resolvedTranscriptsDirSource}
        filter={filter}
        setTranscriptsDir={setTranscriptsDir}
      />
      <LoadingBar loading={isFetching} />
      {error && (
        <ErrorPanel
          title="Error Loading Transcript"
          error={{
            message: error.message || "Unknown Error",
          }}
        />
      )}
      {!error && (
        <>
          <TranscriptFilterBar
            filterCodeValues={filterCodeValues}
            filterSuggestions={filterSuggestions}
            onFilterColumnChange={onFilterColumnChange}
          />
          <TranscriptsGrid
            transcripts={transcripts}
            transcriptsDir={resolvedTranscriptsDir}
            loading={isFetching && transcripts.length === 0}
            onScrollNearEnd={handleScrollNearEnd}
            hasMore={hasNextPage}
            fetchThreshold={TRANSCRIPTS_INFINITE_SCROLL_CONFIG.threshold}
            filterSuggestions={filterSuggestions}
            onFilterColumnChange={onFilterColumnChange}
          />
        </>
      )}
      <Footer
        id={"transcripts-footer"}
        itemCount={data?.pages[0]?.total_count || 0}
        paginated={false}
      />
    </div>
  );
};
