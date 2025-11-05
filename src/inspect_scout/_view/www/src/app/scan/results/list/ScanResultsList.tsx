import { ColumnTable } from "arquero";
import { FC, useCallback, useMemo, useRef } from "react";
import { VirtuosoHandle } from "react-virtuoso";

import { LiveVirtualList } from "../../../../components/LiveVirtualList";

import { ScanResultsRow } from "./ScanResultsRow";
import { ScannerRow } from "./types";

interface ScanResultsListProps {
  columnTable: ColumnTable;
}

// TODO: Need to resolve the dataframe into a better object for rendering
// including resolving some values out of the metadata, etc...
// TODO: mouse hover
// TODO: selectiong?
// TODO: click navigation to detail view
// TODO: display value
// TODO: display id
// TODO: constrain height of explanation, etc...

export const ScanResultsList: FC<ScanResultsListProps> = ({ columnTable }) => {
  const scannerSummaries = useMemo(() => {
    const rowData = columnTable.objects();
    const summaries: ScannerRow[] = rowData.map((row) => {
      const r = row as Record<string, unknown>;
      return {
        id: r.id as string,
        inputType: r.input_type as
          | "transcript"
          | "message"
          | "messages"
          | "event"
          | "events",
        input: JSON.parse(r.input as string),
        value: r.value as string,
        valueType: r.value_type as string,
        explanation: r.explanation as string,
        answer: r.answer as string,
      };
    });
    return summaries;
  }, [columnTable]);

  const listHandle = useRef<VirtuosoHandle | null>(null);
  const renderRow = useCallback((index: number, entry: ScannerRow) => {
    return <ScanResultsRow index={index} entry={entry} />;
  }, []);

  return (
    <div style={{ height: "100%", width: "100%" }}>
      <LiveVirtualList<ScannerRow>
        id="scan-results-list"
        listHandle={listHandle}
        data={scannerSummaries}
        renderRow={renderRow}
      />
    </div>
  );
};
