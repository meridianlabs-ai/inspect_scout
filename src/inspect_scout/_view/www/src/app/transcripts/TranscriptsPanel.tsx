import clsx from "clsx";
import { FC, useCallback, useEffect, useMemo } from "react";

import { ErrorPanel } from "../../components/ErrorPanel";
import { LoadingBar } from "../../components/LoadingBar";
import { Condition, SimpleCondition } from "../../query/types";
import { useStore } from "../../state/store";
import { TranscriptInfo } from "../../types/api-types";
import { Footer } from "../components/Footer";
import { TranscriptsNavbar } from "../components/TranscriptsNavbar";
import { useCode } from "../server/useCode";
import { appAliasedPath, useConfig } from "../server/useConfig";
import { useServerTranscriptsInfinite } from "../server/useServerTranscriptsInfinite";

import { TRANSCRIPTS_INFINITE_SCROLL_CONFIG } from "./constants";
import { TranscriptFilterBar } from "./TranscriptFilterBar";
import { TranscriptsGrid } from "./TranscriptsGrid";
import styles from "./TranscriptsPanel.module.css";

export const TranscriptsPanel: FC = () => {
  // Resolve the active transcripts directory
  const config = useConfig();
  const userTranscriptsDir = useStore((state) => state.userTranscriptsDir);
  const setUserTranscriptsDir = useStore(
    (state) => state.setUserTranscriptsDir
  );
  const resolvedTranscriptDir =
    userTranscriptsDir || config.transcripts_dir || null;

  // Filtering
  const columnFilters =
    useStore((state) => state.transcriptsTableState.columnFilters) ?? {};
  const filterConditions = Object.values(columnFilters)
    .map((filter) => filter.condition)
    .filter((condition): condition is SimpleCondition => Boolean(condition));

  // Sorting
  const condition = filterConditions.reduce<Condition | undefined>(
    (acc, condition) => (acc ? acc.and(condition) : condition),
    undefined
  );
  const sorting = useStore((state) => state.transcriptsTableState.sorting);

  // Clear detail state
  const clearTranscriptState = useStore((state) => state.clearTranscriptState);
  useEffect(() => {
    clearTranscriptState();
  }, [clearTranscriptState]);

  const {
    data: filterCodeValues,
    error: _codeError,
    loading: _codeLoading,
  } = useCode(condition);

  const { data, error, fetchNextPage, hasNextPage, isFetching } =
    useServerTranscriptsInfinite(
      resolvedTranscriptDir,
      TRANSCRIPTS_INFINITE_SCROLL_CONFIG.pageSize,
      condition,
      sorting
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
        transcriptsDir={appAliasedPath(config, resolvedTranscriptDir)}
        setTranscriptsDir={setUserTranscriptsDir}
      ></TranscriptsNavbar>
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
          <TranscriptFilterBar filterCodeValues={filterCodeValues} />
          <TranscriptsGrid
            transcripts={transcripts}
            transcriptsDir={resolvedTranscriptDir}
            loading={isFetching && transcripts.length === 0}
            onScrollNearEnd={handleScrollNearEnd}
            hasMore={hasNextPage}
            fetchThreshold={TRANSCRIPTS_INFINITE_SCROLL_CONFIG.threshold}
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
