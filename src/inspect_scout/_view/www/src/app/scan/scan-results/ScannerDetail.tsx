import { AllCommunityModule, ModuleRegistry } from "ag-grid-community";
import { fromArrow } from "arquero";
import clsx from "clsx";
import { FC, useMemo } from "react";

import { ChatView } from "../../../chat/ChatView";
import { Card, CardBody, CardHeader } from "../../../components/Card";
import { DataframeView } from "../../../components/DataframeView";
import { LabeledValue } from "../../../components/LabeledValue";
import { MarkdownDiv } from "../../../components/MarkdownDiv";
import { useStore } from "../../../state/store";
import { IPCDataframe, Transcript } from "../../../types";
import { firstUserMessage } from "../../../utils/chatMessage";

import styles from "./ScannerDetail.module.css";

interface ScannerDetailProps {
  scanner: IPCDataframe;
}

// Register AG Grid modules
ModuleRegistry.registerModules([AllCommunityModule]);

export const ScannerDetail: FC<ScannerDetailProps> = ({ scanner }) => {
  const selectedResultsView =
    useStore((state) => state.selectedResultsView) || "cards";

  const columnTable = useMemo(() => {
    // Decode base64 string to Uint8Array
    const binaryString = atob(scanner.data);
    const bytes = new Uint8Array(binaryString.length);
    for (let i = 0; i < binaryString.length; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }

    // Load Arrow data using Arquero
    const table = fromArrow(bytes.buffer);
    return table;
  }, [scanner]);

  const scannerSummaries = useMemo(() => {
    const rowData = columnTable.objects();
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
  }, [columnTable]);

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
        <DataframeView columnTable={columnTable} />
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
