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
import { resultIdentifier } from "../../../utils/results";
import { kFilterPositiveResults } from "../ScanResultsFilter";

import { ScanResultsHeader } from "./ScanHeader";
import styles from "./ScanResultsList.module.css";
import { ScanResultsRow } from "./ScanResultsRow";

export interface GridDescriptor {
  gridStyle: Record<string, string>;
  columns: string[];
}

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
  const gridDescriptor = useMemo(() => {
    return optimalColumnLayout(scannerSummaries);
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

  const renderRow = useCallback(
    (index: number, entry: ScannerCore) => {
      return (
        <ScanResultsRow
          index={index}
          entry={entry}
          gridDescriptor={gridDescriptor}
        />
      );
    },
    [gridDescriptor]
  );

  return (
    <div className={clsx(styles.container)}>
      <ScanResultsHeader gridDescriptor={gridDescriptor} />
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

const optimalColumnLayout = (
  scannerSummaries: ScannerCore[]
): GridDescriptor => {
  const columns = [];
  const gridColParts: string[] = [];

  // The id column
  columns.push("id");
  const maxIdLen = scannerSummaries.reduce((max, s) => {
    return Math.max(max, resultIdentifier(s).id.length);
  }, 0);
  gridColParts.push(`${Math.min(Math.max(maxIdLen * 8, 50), 250)}px`);

  // The explanation column, if any explanations exist
  const hasExplanation = scannerSummaries.some((s) => !!s.explanation);
  if (hasExplanation) {
    columns.push("explanation");
    gridColParts.push("10fr");
  }

  // The label column, if any labels exist
  const hasLabel = scannerSummaries.some((s) => !!s.label);
  if (hasLabel) {
    columns.push("label");

    const maxlabelLen = scannerSummaries.reduce((max, s) => {
      return Math.max(max, resultIdentifier(s).id.length);
    }, 0);
    gridColParts.push(`${Math.min(Math.max(maxlabelLen * 4, 50), 250)}px`);
  }

  // The value column
  columns.push("value");
  const hasValueObjs = scannerSummaries.some((s) => s.valueType === "object");
  if (hasValueObjs) {
    gridColParts.push("5fr");
  } else {
    const maxValueLen = scannerSummaries.reduce((max: number, s) => {
      if (s.valueType === "array") {
        const len = (s.value as unknown[]).reduce<number>((prev, val) => {
          const valStr = val !== undefined && val !== null ? String(val) : "";
          return Math.max(prev, valStr.length);
        }, 0);
        return Math.max(max, len);
      } else {
        const valStr =
          s.value !== undefined && s.value !== null ? String(s.value) : "";
        return Math.max(max, valStr.length);
      }
    }, 0);
    gridColParts.push(`${Math.min(Math.max(maxValueLen * 4, 50), 300)}px`);
  }

  // Special case - if there is only an id and value column, divide space evenly
  if (columns.length === 2 && columns[0] === "id" && columns[1] === "value") {
    gridColParts[0] = "1fr";
    gridColParts[1] = "1fr";
  }

  return {
    gridStyle: {
      gridTemplateColumns: gridColParts.join(" "),
      display: "grid",
      columnGap: "0.5rem",
    },
    columns,
  };
};
