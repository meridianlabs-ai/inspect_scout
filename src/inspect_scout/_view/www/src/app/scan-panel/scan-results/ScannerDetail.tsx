import { FC, useMemo } from "react";
import { fromArrow } from "arquero";
import {
  AllCommunityModule,
  ModuleRegistry,
  themeBalham,
  type ColDef,
  type StateUpdatedEvent,
} from "ag-grid-community";
import { AgGridReact } from "ag-grid-react";

import { IPCDataframe, Transcript } from "../../../types";
import { Card, CardBody, CardHeader } from "../../../components/Card";
import { ChatView } from "../../../chat/ChatView";
import { LabeledValue } from "../../../components/LabeledValue";
import clsx from "clsx";

import styles from "./ScannerDetail.module.css";
import { MarkdownDiv } from "../../../components/MarkdownDiv";
import { firstUserMessage } from "../../../utils/chatMessage";
import { useStore } from "../../../state/store";

interface ScannerDetailProps {
  scanner: IPCDataframe;
}

// Register AG Grid modules
ModuleRegistry.registerModules([AllCommunityModule]);

const kFilterPrefix: string[] = [];
const kMultilineColumns: string[] = [];
const GRID_STATE_NAME = "ScannerDetailGrid";

export const ScannerDetail: FC<ScannerDetailProps> = ({ scanner }) => {
  const selectedResultsView =
    useStore((state) => state.selectedResultsView) || "cards";

  const gridStates = useStore((state) => state.gridStates);
  const setGridState = useStore((state) => state.setGridState);

  const { columnDefs, rowData } = useMemo(() => {
    // Decode base64 string to Uint8Array
    const binaryString = atob(scanner.data);
    const bytes = new Uint8Array(binaryString.length);
    for (let i = 0; i < binaryString.length; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }

    // Load Arrow data using Arquero
    const table = fromArrow(bytes.buffer);

    // Create column definitions for ag-grid
    const columnDefs: ColDef[] = scanner.column_names
      .filter((name) => {
        return !kFilterPrefix.some((prefix) => name.startsWith(prefix));
      })
      .map((name) => {
        const isMultiline = kMultilineColumns.includes(name);
        return {
          field: name,
          headerName: name,
          sortable: true,
          filter: true,
          resizable: true,
          wrapText: true,
          autoHeight: isMultiline,
          minWidth: isMultiline ? 300 : 75,
          tooltipField: name,
        };
      });

    // Convert table to array of objects for ag-grid
    const rowData = table.objects();

    return { columnDefs, rowData };
  }, [scanner]);

  const gridState = useMemo(() => {
    const savedState = gridStates[GRID_STATE_NAME];
    // If no saved state, return undefined to use default grid state
    return savedState;
  }, [gridStates]);

  const scannerSummaries = useMemo(() => {
    const summaries: ScannerRow[] = rowData.map((row) => {
      const r = row as Record<string, unknown>;
      return {
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
  }, [rowData]);

  return (
    <div style={{ height: "100%", width: "100%" }}>
      {selectedResultsView === "cards" && (
        <div className={clsx("text-size-small")}>
          {scannerSummaries.map((summary, index) => (
            <Card key={`scanner-summary-card-${index}`}>
              <CardHeader label={`Scanner Summary ${index + 1}`} />
              <CardBody>
                <div className={clsx(styles.scannerHeaderRow)}>
                  <LabeledValue label="Value">
                    {summary.value || "(none)"}
                  </LabeledValue>
                  <LabeledValue label="Answer">
                    {summary.answer || "(none)"}
                  </LabeledValue>
                </div>
                <LabeledValue label="Input">
                  <RenderedScannerInput
                    row={summary}
                    id={`scanner-input-${index}`}
                  />
                </LabeledValue>
                <LabeledValue label="Explanation">
                  <MarkdownDiv markdown={summary.explanation} />
                </LabeledValue>
              </CardBody>
            </Card>
          ))}
        </div>
      )}
      {selectedResultsView === "grid" && (
        <div className={styles.gridWrapper}>
          <AgGridReact
            rowData={rowData}
            columnDefs={columnDefs}
            defaultColDef={{
              sortable: true,
              filter: true,
              resizable: true,
            }}
            rowHeight={100}
            animateRows={false}
            suppressColumnMoveAnimation={true}
            suppressCellFocus={true}
            theme={themeBalham}
            enableCellTextSelection={true}
            autoSizeStrategy={{ type: "fitGridWidth" }}
            initialState={gridState}
            onStateUpdated={(e: StateUpdatedEvent) => {
              setGridState(GRID_STATE_NAME, e.state);
            }}
          />
        </div>
      )}
    </div>
  );
};

interface ScannerRow {
  inputType: "transcript" | "message" | "messages" | "event" | "events";
  input: unknown;
  value: string;
  valueType: string;
  explanation: string;
  answer: string;
}

const RenderedScannerInput: FC<{ row: ScannerRow; id: string }> = ({
  row,
  id,
}) => {
  switch (row.inputType) {
    case "transcript": {
      const transcript = row.input as Transcript;
      const messages = transcript.messages;
      const previewMessage = firstUserMessage(messages);
      if (!previewMessage) {
        return <div>No messages in transcript.</div>;
      }
      return <ChatView id={id} messages={[previewMessage]} />;
    }
    case "message":
      return <ChatView id={id} messages={[row.input] as any[]} />;
    case "messages":
      return <ChatView id={id} messages={row.input as any[]} />;
    case "events":
    case "event":
      return <div>Events</div>;
  }
};
