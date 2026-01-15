import { skipToken } from "@tanstack/react-query";
import clsx from "clsx";
import { FC, useCallback, useEffect, useMemo, useState } from "react";

import { ErrorPanel } from "../../components/ErrorPanel";
import { LoadingBar } from "../../components/LoadingBar";
import { useStore } from "../../state/store";
import { TranscriptInfo } from "../../types/api-types";
import { Footer } from "../components/Footer";
import { TranscriptsNavbar } from "../components/TranscriptsNavbar";
import { useFilterConditions } from "../hooks/useFilterConditions";
import { useCode } from "../server/useCode";
import { appAliasedPath, useConfig } from "../server/useConfig";
import { useServerTranscriptsInfinite } from "../server/useServerTranscriptsInfinite";
import { useTranscriptsColumnValues } from "../server/useTranscriptsColumnValues";

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

  const sorting = useStore((state) => state.transcriptsTableState.sorting);
  const condition = useFilterConditions();

  // Filter for autocomplete: exclude the column being edited
  const [editingColumnId, setEditingColumnId] = useState<string | null>(null);
  const otherColumnsFilter = useFilterConditions(editingColumnId ?? undefined);

  // Clear detail state
  const clearTranscriptState = useStore((state) => state.clearTranscriptState);
  useEffect(() => {
    clearTranscriptState();
  }, [clearTranscriptState]);

  const {
    data: filterCodeValues,
    error: _codeError,
    loading: _codeLoading,
  } = useCode(condition ?? skipToken);

  // Fetch column values for autocomplete suggestions (scoped to other column filters)
  const {
    data: filterBarSuggestions,
    loading: _suggestionsLoading,
    error: _suggestionsError,
  } = useTranscriptsColumnValues(
    editingColumnId && resolvedTranscriptDir
      ? {
          location: resolvedTranscriptDir,
          column: editingColumnId,
          filter: otherColumnsFilter,
        }
      : skipToken
  );

  const { data, error, fetchNextPage, hasNextPage, isFetching } =
    useServerTranscriptsInfinite(
      resolvedTranscriptDir
        ? {
            location: resolvedTranscriptDir,
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
          <TranscriptFilterBar
            filterCodeValues={filterCodeValues}
            filterSuggestions={filterBarSuggestions ?? []}
            onFilterColumnChange={setEditingColumnId}
          />
          <TranscriptsGrid
            transcripts={transcripts}
            transcriptsDir={resolvedTranscriptDir}
            loading={isFetching && transcripts.length === 0}
            onScrollNearEnd={handleScrollNearEnd}
            hasMore={hasNextPage}
            fetchThreshold={TRANSCRIPTS_INFINITE_SCROLL_CONFIG.threshold}
            filterSuggestions={filterBarSuggestions ?? []}
            onFilterColumnChange={setEditingColumnId}
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
