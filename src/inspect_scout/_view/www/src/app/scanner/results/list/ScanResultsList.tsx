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
  const isLoadingData = useStore((state) => state.loadingData);
  const busy = isLoading || isLoadingData;
  const listHandle = useRef<VirtuosoHandle | null>(null);
  const hasExplanation = useMemo(() => {
    return scannerSummaries.some((s) => !!s.explanation);
  }, [scannerSummaries]);

  const filteredSummaries = useMemo(() => {
    if (
      selectedFilter === kFilterPositiveResults ||
      selectedFilter === undefined
    ) {
      return scannerSummaries.filter((s) => !!s.value);
    } else {
      return scannerSummaries;
    }
  }, [scannerSummaries, selectedFilter]);
  const selectedScanResult = useStore((state) => state.selectedScanResult);

  const initialTopMostItemIndex = useMemo(() => {
    if (selectedScanResult) {
      const selectedIndex = filteredSummaries.findIndex(
        (s) => s.uuid === selectedScanResult
      );
      if (selectedIndex >= 0) {
        return selectedIndex;
      }
    }
    return undefined;
  }, [selectedScanResult, filteredSummaries]);

  const gridTemplateColumns = useMemo(() => {
    const complexValue = filteredSummaries.some(
      (s) => s.valueType === "object" || s.valueType === "array"
    );
    const valueColumn = complexValue ? "7fr" : "2fr";

    return hasExplanation ? `1fr 10fr ${valueColumn}` : `1fr ${valueColumn}`;
  }, [hasExplanation, filteredSummaries]);

  const renderRow = useCallback(
    (index: number, entry: ScannerCore) => {
      return (
        <ScanResultsRow
          index={index}
          entry={entry}
          hasExplanation={hasExplanation}
          gridTemplateColumns={gridTemplateColumns}
        />
      );
    },
    [hasExplanation]
  );

  return (
    <div className={clsx(styles.container)}>
      <ScanResultsHeader
        gridTemplateColumns={gridTemplateColumns}
        hasExplanation={hasExplanation}
      />
      <ActivityBar animating={isLoading} />
      {!busy && filteredSummaries.length === 0 && (
        <NoContentsPanel text="No scan results to display." />
      )}
      {!busy && filteredSummaries.length > 0 && (
        <LiveVirtualList<ScannerCore>
          id={id}
          listHandle={listHandle}
          data={filteredSummaries}
          renderRow={renderRow}
          className={clsx(styles.list)}
          initialTopMostItemIndex={initialTopMostItemIndex}
        />
      )}
    </div>
  );
};
