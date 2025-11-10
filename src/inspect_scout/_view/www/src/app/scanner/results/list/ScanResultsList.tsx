import { ColumnTable } from "arquero";
import clsx from "clsx";
import { FC, useCallback, useMemo, useRef } from "react";
import { VirtuosoHandle } from "react-virtuoso";

import { ActivityBar } from "../../../../components/ActivityBar";
import { LiveVirtualList } from "../../../../components/LiveVirtualList";
import { NoContentsPanel } from "../../../../components/NoContentsPanel";
import { useStore } from "../../../../state/store";
import { useScannerPreviews } from "../../../hooks";
import { ScannerCore } from "../../../types";
import { kFilterPositiveResults } from "../ScanResultsFilter";

import { ScanResultsHeader } from "./ScanHeader";
import styles from "./ScanResultsList.module.css";
import { ScanResultsRow } from "./ScanResultsRow";

interface ScanResultsListProps {
  id: string;
  columnTable: ColumnTable;
}
// TODO: Keyboard navigation
// TODO: Ensure selected item is scrolled into view

export const ScanResultsList: FC<ScanResultsListProps> = ({
  id,
  columnTable,
}) => {
  const { data: scannerSummaries, isLoading } = useScannerPreviews(columnTable);
  const selectedFilter = useStore((state) => state.selectedFilter);
  const listHandle = useRef<VirtuosoHandle | null>(null);
  const hasExplanation = useMemo(() => {
    return scannerSummaries.some((s) => !!s.explanation);
  }, [scannerSummaries]);

  const filteredScanners = useMemo(() => {
    if (
      selectedFilter === kFilterPositiveResults ||
      selectedFilter === undefined
    ) {
      return scannerSummaries.filter((s) => !!s.value);
    } else {
      return scannerSummaries;
    }
  }, [scannerSummaries, selectedFilter]);

  const renderRow = useCallback(
    (index: number, entry: ScannerCore) => {
      return (
        <ScanResultsRow
          index={index}
          entry={entry}
          hasExplanation={hasExplanation}
        />
      );
    },
    [hasExplanation]
  );

  return (
    <div className={clsx(styles.container)}>
      <ScanResultsHeader hasExplanation={hasExplanation} />
      <ActivityBar animating={isLoading} />
      {!isLoading && filteredScanners.length === 0 && (
        <NoContentsPanel text="No scan results to display." />
      )}
      {!isLoading && filteredScanners.length > 0 && (
        <LiveVirtualList<ScannerCore>
          id={id}
          listHandle={listHandle}
          data={filteredScanners}
          renderRow={renderRow}
          className={clsx(styles.list)}
        />
      )}
    </div>
  );
};
