import { FC, useMemo } from "react";
import { fromArrow } from "arquero";
import { type ColDef } from "ag-grid-community";

import {
  ChatMessage,
  ChatMessages,
  IPCDataframe,
  Transcript,
} from "../../../types";
import { Card, CardBody, CardHeader } from "../../../components/Card";
import { ChatView } from "../../../chat/ChatView";
import { LabeledValue } from "../../../components/LabeledValue";
import clsx from "clsx";

import styles from "./ScannerDetail.module.css";

interface ScannerDetailProps {
  scanner: IPCDataframe;
}

const kFilterPrefix = ["scan_", "transcript_", "scanner_"];
const kMultilineColumns = ["input", "explanation"];

export const ScannerDetail: FC<ScannerDetailProps> = ({ scanner }) => {
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
          wrapText: isMultiline,
          autoHeight: isMultiline,
          minWidth: isMultiline ? 300 : 75,
        };
      });

    // Convert table to array of objects for ag-grid
    const rowData = table.objects();

    return { columnDefs, rowData };
  }, [scanner]);

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
                {summary.explanation}
              </LabeledValue>
            </CardBody>
          </Card>
        ))}
      </div>
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
      const lastMessage = lastAssistantMessage(messages);
      if (!lastMessage) {
        return <div>No messages in transcript.</div>;
      }
      return <ChatView id={id} messages={[lastMessage]} />;
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

const lastAssistantMessage = (
  messages: ChatMessages
): ChatMessage | undefined => {
  for (let i = messages.length - 1; i >= 0; i--) {
    if (messages[i]?.role === "assistant") {
      return messages[i];
    }
  }
  return undefined;
};
