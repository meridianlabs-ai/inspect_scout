import { clsx } from "clsx";
import { FC, useCallback, useEffect, useMemo } from "react";

import { ErrorPanel } from "../../components/ErrorPanel";
import { ExtendedFindProvider } from "../../components/ExtendedFindProvider";
import { ApplicationIcons } from "../../components/icons";
import { LoadingBar } from "../../components/LoadingBar";
import { NoContentsPanel } from "../../components/NoContentsPanel";
import { useStore } from "../../state/store";
import { ScanStatusWithActiveInfo } from "../../types/api-types";
import { Footer } from "../components/Footer";
import { ScansNavbar } from "../components/ScansNavbar";
import { useScanFilterConditions } from "../hooks/useScanFilterConditions";
import { useScansFilterBarProps } from "../hooks/useScansFilterBarProps";
import { useAppConfig } from "../server/useAppConfig";
import { useScansInfinite } from "../server/useScansInfinite";
import { useScansDir } from "../utils/useScansDir";

import { SCANS_INFINITE_SCROLL_CONFIG } from "./constants";
import { ScansFilterBar } from "./ScansFilterBar";
import { ScansGrid } from "./ScansGrid";
import styles from "./ScansPanel.module.css";

export const ScansPanel: FC = () => {
  const config = useAppConfig();
  const scanDir = config.scans.dir;
  const {
    displayScansDir,
    resolvedScansDir,
    resolvedScansDirSource,
    setScansDir,
  } = useScansDir();

  // Get filter condition and sorting from store
  const condition = useScanFilterConditions();
  const sorting = useStore((state) => state.scansTableState.sorting);

  // Get autocomplete props for filter bar
  const { filterSuggestions, onFilterColumnChange } =
    useScansFilterBarProps(resolvedScansDir);

  // Load scans data with filtering and sorting
  const { data, error, fetchNextPage, hasNextPage, isFetching } =
    useScansInfinite(
      resolvedScansDir,
      SCANS_INFINITE_SCROLL_CONFIG.pageSize,
      condition,
      sorting
    );

  // Flatten pages into scans array
  const scans: ScanStatusWithActiveInfo[] = useMemo(
    () => data?.pages.flatMap((page) => page.items) ?? [],
    [data]
  );

  // Handle infinite scroll
  const handleScrollNearEnd = useCallback(() => {
    fetchNextPage({ cancelRefetch: false }).catch(console.error);
  }, [fetchNextPage]);

  // Clear scan state from store on mount
  const clearScansState = useStore((state) => state.clearScansState);
  useEffect(() => {
    clearScansState();
  }, [clearScansState]);

  return (
    <div className={clsx(styles.container)}>
      <ScansNavbar
        scansDir={displayScansDir}
        scansDirSource={resolvedScansDirSource}
        setScansDir={setScansDir}
        bordered={true}
      />
      <LoadingBar loading={isFetching} />
      <ExtendedFindProvider>
        {error && (
          <ErrorPanel
            title="Error Loading Scans"
            error={{ message: error.message }}
          />
        )}
        {!data && !error && (
          <NoContentsPanel icon={ApplicationIcons.running} text="Loading..." />
        )}
        {data && !error && (
          <div className={styles.gridContainer}>
            <ScansFilterBar
              filterSuggestions={filterSuggestions}
              onFilterColumnChange={onFilterColumnChange}
            />
            <ScansGrid
              scans={scans}
              resultsDir={scanDir}
              loading={isFetching && scans.length === 0}
              className={styles.grid}
              onScrollNearEnd={handleScrollNearEnd}
              hasMore={hasNextPage}
              fetchThreshold={SCANS_INFINITE_SCROLL_CONFIG.threshold}
              filterSuggestions={filterSuggestions}
              onFilterColumnChange={onFilterColumnChange}
            />
          </div>
        )}
        <Footer
          id={"scan-job-footer"}
          itemCount={data?.pages[0]?.total_count ?? 0}
          paginated={false}
        />
      </ExtendedFindProvider>
    </div>
  );
};
