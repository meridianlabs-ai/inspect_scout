import { ColumnTable } from "arquero";
import clsx from "clsx";
import { FC, useCallback, useRef } from "react";
import { VirtuosoHandle } from "react-virtuoso";

import { LiveVirtualList } from "../../../../components/LiveVirtualList";

import { useScannerPreviews } from "./hooks";
import { ScanResultsHeader } from "./ScanHeader";
import styles from "./ScanResultsList.module.css";
import { ScanResultsRow } from "./ScanResultsRow";
import { ScannerPreview } from "./types";

interface ScanResultsListProps {
  columnTable: ColumnTable;
}
// TODO: Filter by results value
// TODO: Keyboard navigation
// TODO: Ensure selected item is scrolled into view

export const ScanResultsList: FC<ScanResultsListProps> = ({ columnTable }) => {
  const scannerSummaries = useScannerPreviews(columnTable);
  const listHandle = useRef<VirtuosoHandle | null>(null);
  const renderRow = useCallback((index: number, entry: ScannerPreview) => {
    return <ScanResultsRow index={index} entry={entry} />;
  }, []);

  return (
    <div className={clsx(styles.container)}>
      <ScanResultsHeader />
      <LiveVirtualList<ScannerPreview>
        id="scan-results-list"
        listHandle={listHandle}
        data={scannerSummaries}
        renderRow={renderRow}
        className={clsx(styles.list)}
      />
    </div>
  );
};
