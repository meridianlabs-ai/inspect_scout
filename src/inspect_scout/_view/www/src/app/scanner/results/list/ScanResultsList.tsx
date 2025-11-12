import { ColumnTable } from "arquero";
import clsx from "clsx";
import { FC, use, useCallback, useMemo, useRef } from "react";
import { VirtuosoHandle } from "react-virtuoso";

import { ActivityBar } from "../../../../components/ActivityBar";
import { LiveVirtualList } from "../../../../components/LiveVirtualList";
import { NoContentsPanel } from "../../../../components/NoContentsPanel";
import { useStore } from "../../../../state/store";
import { useScannerPreviews } from "../../../hooks";
import { ScannerCore } from "../../../types";
import { resultIdentifier } from "../../../utils/results";
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
  const hasLabel = useMemo(() => {
    return scannerSummaries.some((s) => !!s.label);
  }, [scannerSummaries]);

  const filteredSummaries = useMemo(() => {
    if (
      selectedFilter === kFilterPositiveResults ||
      selectedFilter === undefined
    ) {
      return scannerSummaries.filter((s) => !!s.value).sort(sortByIdentifier);
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
    const valueColumn = complexValue ? "250px" : "150px";
    const labelColumn = hasLabel ? "150px" : "";

    return hasExplanation
      ? `140px 10fr ${labelColumn} ${valueColumn}`
      : `140px ${labelColumn} ${valueColumn}`;
  }, [hasExplanation, filteredSummaries]);

  const renderRow = useCallback(
    (index: number, entry: ScannerCore) => {
      return (
        <ScanResultsRow
          index={index}
          entry={entry}
          hasExplanation={hasExplanation}
          hasLabel={hasLabel}
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
        hasLabel={hasLabel}
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

const sortByIdentifier = (a: ScannerCore, b: ScannerCore): number => {
  // Sort first by id
  const identifierA = resultIdentifier(a);
  const identifierB = resultIdentifier(b);
  const idComparison = identifierA.id.localeCompare(identifierB.id);

  if (idComparison !== 0) {
    return idComparison;
  }

  // then by epoch
  if (identifierA.epoch && identifierB.epoch) {
    return identifierA.epoch.localeCompare(identifierB.epoch);
  }

  if (identifierA.epoch) {
    return -1;
  }
  if (identifierB.epoch) {
    return 1;
  }

  return 0;
};
