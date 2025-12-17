import clsx from "clsx";
import { FC, ReactNode } from "react";

import { EventType } from "../../transcript/types";
import { Status, Transcript } from "../../types";
import { Events, Messages } from "../../types/log";
import {
  ScanResultInputData,
  isEventInput,
  isEventsInput,
  isMessageInput,
  isMessagesInput,
  isTranscriptInput,
  ScanResultData,
  MessageType,
} from "../types";

import styles from "./ScanResultHeader.module.css";

interface ScanResultHeaderProps {
  result?: ScanResultData;
  status?: Status;
  inputData?: ScanResultInputData;
}

interface Column {
  label: string;
  value: ReactNode;
  className?: string | string[];
}

export const ScanResultHeader: FC<ScanResultHeaderProps> = ({
  status,
  inputData,
}) => {
  const columns = colsForResult(inputData, status) || [];

  return (
    <div className={clsx(styles.header, classForCols(columns.length))}>
      {columns.map((col) => {
        return (
          <div
            key={`header-label-${col.label}`}
            className={clsx(
              "text-size-smallest",
              "text-style-label",
              "text-style-secondary",
              styles.label,
              col.className
            )}
          >
            {col.label}
          </div>
        );
      })}

      {columns.map((col) => {
        return (
          <div
            key={`header-val-${col.label}`}
            className={clsx("text-size-small", styles.value, col.className)}
          >
            {col.value}
          </div>
        );
      })}
    </div>
  );
};

const classForCols = (numCols: number) => {
  return clsx(
    numCols === 1
      ? styles.oneCol
      : numCols === 2
        ? styles.twoCol
        : numCols === 3
          ? styles.threeCol
          : numCols === 4
            ? styles.fourCol
            : numCols === 5
              ? styles.fiveCol
              : styles.sixCol
  );
};

const colsForResult: (
  inputData?: ScanResultInputData,
  status?: Status
) => Column[] | undefined = (inputData, status) => {
  if (!inputData) {
    return [];
  }
  if (isTranscriptInput(inputData)) {
    return transcriptCols(inputData.input, status);
  } else if (isMessageInput(inputData)) {
    return messageCols(inputData.input, status);
  } else if (isMessagesInput(inputData)) {
    return messagesCols(inputData.input);
  } else if (isEventInput(inputData)) {
    return eventCols(inputData.input);
  } else if (isEventsInput(inputData)) {
    return eventsCols(inputData.input);
  } else {
    return [];
  }
};

const transcriptCols = (transcript: Transcript, status?: Status) => {
  // Read values from the transcript directly, falling back to metadata
  // The metadata was previously used to store these values before they were
  // added to the main Transcript schema (so we're doing this mainly for backwards
  // compatibility with old scan results)
  const datasourceUri = transcript.source_uri || transcript.metadata?.log;
  const taskName = transcript.task || transcript.metadata?.task_name;
  const transcriptId =
    transcript.metadata?.id && transcript.metadata?.epoch
      ? `${transcript.metadata?.id} Epoch ${transcript.metadata?.epoch}`
      : transcript.id;
  const transcriptModel = transcript.model || transcript.metadata?.model;
  const scanningModel = status?.spec.model.model;

  const cols: Column[] = [
    {
      label: "Source",
      value: datasourceUri,
    },
    {
      label: "Task",
      value: taskName,
    },

    {
      label: "Id",
      value: transcriptId,
    },

    {
      label: "Model",
      value: transcriptModel,
    },
  ];

  if (status?.spec.model.model) {
    cols.push({
      label: "Scanning Model",
      value: scanningModel,
    });
  }
  return cols;
};

const messageCols = (message: MessageType, status?: Status) => {
  const cols: Column[] = [
    {
      label: "Message ID",
      value: message.id,
    },
  ];

  if (message.role === "assistant") {
    cols.push({
      label: "Model",
      value: message.model,
    });
    cols.push({
      label: "Tool Calls",
      value: ((message.tool_calls as []) || []).length,
    });
  } else {
    cols.push({
      label: "Role",
      value: message.role,
    });
  }

  if (status?.spec.model.model) {
    cols.push({
      label: "Scanning Model",
      value: status.spec.model.model,
    });
  }

  return cols;
};

const messagesCols = (messages: Messages): Column[] => {
  return [
    {
      label: "Message Count",
      value: messages.length,
    },
  ];
};

const eventCols = (event: EventType): Column[] => {
  return [
    {
      label: "Event Type",
      value: event.event,
    },
    {
      label: "Timestamp",
      value: new Date(event.timestamp).toLocaleString(),
    },
  ];
};

const eventsCols = (events: Events): Column[] => {
  return [
    {
      label: "Event Count",
      value: events.length,
    },
  ];
};
