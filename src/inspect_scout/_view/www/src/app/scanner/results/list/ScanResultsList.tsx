import { ColumnTable } from "arquero";
import clsx from "clsx";
import { FC, useCallback, useMemo, useRef } from "react";
import { VirtuosoHandle } from "react-virtuoso";

import { LiveVirtualList } from "../../../../components/LiveVirtualList";
import { useScannerPreviews } from "../../../hooks";
import { ScannerCore } from "../../../types";

import { ScanResultsHeader } from "./ScanHeader";
import styles from "./ScanResultsList.module.css";
import { ScanResultsRow } from "./ScanResultsRow";

interface ScanResultsListProps {
  id: string;
  columnTable: ColumnTable;
}
// TODO: Filter by results value
// TODO: Keyboard navigation
// TODO: Ensure selected item is scrolled into view

export const ScanResultsList: FC<ScanResultsListProps> = ({
  id,
  columnTable,
}) => {
  const scannerSummaries = useScannerPreviews(columnTable);
  const listHandle = useRef<VirtuosoHandle | null>(null);
  const hasExplanation = useMemo(() => {
    return scannerSummaries.some((s) => !!s.explanation);
  }, [scannerSummaries]);

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
      <LiveVirtualList<ScannerCore>
        id={id}
        listHandle={listHandle}
        data={scannerSummaries}
        renderRow={renderRow}
        className={clsx(styles.list)}
      />
    </div>
  );
};
