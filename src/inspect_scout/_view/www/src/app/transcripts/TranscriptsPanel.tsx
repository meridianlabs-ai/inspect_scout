import clsx from "clsx";
import { FC, useCallback, useEffect, useMemo, useRef, useState } from "react";

import { ErrorPanel } from "../../components/ErrorPanel";
import { LoadingBar } from "../../components/LoadingBar";
import { Condition, SimpleCondition } from "../../query/types";
import { useStore } from "../../state/store";
import { TranscriptInfo } from "../../types/api-types";
import { Footer } from "../components/Footer";
import { TranscriptsNavbar } from "../components/TranscriptsNavbar";
import { useCode } from "../server/useCode";
import { useConfig } from "../server/useConfig";
import { useServerTranscriptsInfinite } from "../server/useServerTranscriptsInfinite";

import { TranscriptColumnsButton } from "./TranscriptColumnsButton";
import { TranscriptColumnsPopover } from "./TranscriptColumnsPopover";
import { TranscriptFilterBar } from "./TranscriptFilterBar";
import { TranscriptsGrid } from "./TranscriptsGrid";
import styles from "./TranscriptsPanel.module.css";

export const TranscriptsPanel: FC = () => {
  // Column picker state
  const [showColumnPicker, setShowColumnPicker] = useState(false);
  const columnButtonRef = useRef<HTMLButtonElement>(null);

  // Resolve the active transcripts directory
  const config = useConfig();
  const transcriptDir = config.transcripts_dir;
  const userTranscriptsDir = useStore((state) => state.userTranscriptsDir);
  const setUserTranscriptsDir = useStore(
    (state) => state.setUserTranscriptsDir
  );
  const resolvedTranscriptDir = userTranscriptsDir || transcriptDir;

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
    error: codeError,
    loading,
  } = useCode(condition);

  const { data, error, fetchNextPage, hasNextPage, isFetching } =
    useServerTranscriptsInfinite(
      resolvedTranscriptDir,
      infiniteScrollConfig.pageSize,
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
        transcriptsDir={resolvedTranscriptDir}
        setTranscriptsDir={setUserTranscriptsDir}
      >
        <TranscriptColumnsButton
          ref={columnButtonRef}
          isOpen={showColumnPicker}
          onClick={() => setShowColumnPicker(!showColumnPicker)}
        />
      </TranscriptsNavbar>
      <TranscriptColumnsPopover
        positionEl={columnButtonRef.current}
        isOpen={showColumnPicker}
        setIsOpen={setShowColumnPicker}
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
          <TranscriptFilterBar filterCodeValues={filterCodeValues} />
          <TranscriptsGrid
            transcripts={transcripts}
            transcriptsDir={resolvedTranscriptDir}
            loading={isFetching && transcripts.length === 0}
            onScrollNearEnd={handleScrollNearEnd}
            hasMore={hasNextPage}
            fetchThreshold={infiniteScrollConfig.threshold}
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

/**
 * Infinite Scroll Tuning
 *
 * Goal: user never hits bottom while waiting for next page.
 *
 * Formula: threshold >= scroll_speed × fetch_duration
 *
 * Assumptions:
 *   row_height = 29px
 *   fetch_duration = 300-1000ms (variable with fixed overhead)
 *   max_scroll_speed = 1500px/s (typical fast scroller)
 *
 * Check at typical speed (1500px/s):
 *   runway_time = 2000px / 1500px/s = 1333ms
 *   worst_case_fetch = 1000ms
 *   margin = 333ms ✓
 *
 * Check at extreme speed (5000px/s):
 *   runway_time = 2000px / 5000px/s = 400ms
 *   median_fetch = ~350ms
 *   margin = 50ms (tight but ok) ✓
 *
 * Why large pageSize? Fetch duration is mostly fixed overhead, so larger
 * pages = fewer fetches = fewer stall opportunities. 500 rows gives ~9.7s
 * of scrolling per page at 1500px/s.
 *
 * Note: If threshold > pageSize_px, the next page is prefetched immediately
 * after the current page loads. This is fine for maximum smoothness.
 */
const infiniteScrollConfig = {
  /** Number of rows to fetch per page (500 rows = 14,500px at 29px/row) */
  pageSize: 500,
  /** Distance from bottom (in px) at which to trigger fetch (~69 rows) */
  threshold: 2000,
};
