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
  const cols = [
    {
      label: "Log",
      value: transcript.metadata?.log as ReactNode,
    },
    {
      label: "Task",
      value: (transcript.task || transcript.metadata?.task_name) as ReactNode,
    },

    {
      label: "Sample Id",
      value:
        `${transcript.metadata?.id} Epoch ${transcript.metadata?.epoch}` as ReactNode,
    },

    {
      label: "Model",
      value: transcript.metadata?.model as ReactNode,
    },
  ];

  if (status?.spec.model.model) {
    cols.push({
      label: "Scanning Model",
      value: status.spec.model.model as ReactNode,
    });
  }
  return cols;
};

const messageCols = (message: MessageType, status?: Status) => {
  const cols = [
    {
      label: "Message ID",
      value: message.id as ReactNode,
    },
  ];

  if (message.role === "assistant") {
    cols.push({
      label: "Model",
      value: message.model as ReactNode,
    });
    cols.push({
      label: "Tool Calls",
      value: ((message.tool_calls as []) || []).length as ReactNode,
    });
  } else {
    cols.push({
      label: "Role",
      value: message.role as ReactNode,
    });
  }

  if (status?.spec.model.model) {
    cols.push({
      label: "Scanning Model",
      value: status.spec.model.model as ReactNode,
    });
  }

  return cols;
};

const messagesCols = (messages: Messages) => {
  return [
    {
      label: "Message Count",
      value: messages.length as ReactNode,
    },
  ];
};

const eventCols = (event: EventType) => {
  return [
    {
      label: "Event Type",
      value: event.event as ReactNode,
    },
    {
      label: "Timestamp",
      value: new Date(event.timestamp).toLocaleString() as ReactNode,
    },
  ];
};

const eventsCols = (events: Events) => {
  return [
    {
      label: "Event Count",
      value: events.length as ReactNode,
    },
  ];
};
