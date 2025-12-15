import clsx from "clsx";
import { FC, ReactNode } from "react";

import { Status } from "../../types";
import { filename } from "../../utils/path";
import { ScannerData } from "../types";

import styles from "./ScanResultHeader.module.css";

interface ScanResultHeaderProps {
  result?: ScannerData;
  status?: Status;
}

interface Column {
  label: string;
  value: ReactNode;
  className?: string | string[];
}

export const ScanResultHeader: FC<ScanResultHeaderProps> = ({
  result,
  status,
}) => {
  const columns = colsForResult(result, status) || [];

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
  result?: ScannerData,
  status?: Status
) => Column[] | undefined = (result, status) => {
  if (!result) {
    return [];
  }
  if (result.inputType === "transcript") {
    return transcriptCols(result, status);
  } else if (result.inputType === "message") {
    return messageCols(result, status);
  } else if (result.inputType === "messages") {
    return messagesCols(result);
  } else if (result.inputType === "event") {
    return eventCols(result);
  } else if (result.inputType === "events") {
    return eventsCols(result);
  } else {
    return [];
  }
};

const transcriptCols = (result: ScannerData, status?: Status) => {
  if (result.inputType === "transcript") {
    const cols = [
      {
        label: "Log",
        value: filename(result.input.metadata.log) as ReactNode,
      },
      {
        label: "Task",
        value: (result.input.metadata.task_ ||
          result.input.metadata.task_name ||
          "") as ReactNode,
      },

      {
        label: "Sample Id",
        value:
          `${result.input.metadata.id} Epoch ${result.input.metadata.epoch}` as ReactNode,
      },

      {
        label: "Model",
        value: result.input.metadata.model as ReactNode,
      },
    ];

    if (status?.spec.model.model) {
      cols.push({
        label: "Scanning Model",
        value: status.spec.model.model as ReactNode,
      });
    }
    return cols;
  }
};

const messageCols = (result: ScannerData, status?: Status) => {
  if (result.inputType === "message") {
    const cols = [
      {
        label: "Message ID",
        value: result.input.id as ReactNode,
      },
    ];

    if (result.input.role === "assistant") {
      cols.push({
        label: "Model",
        value: result.input.model as ReactNode,
      });
      cols.push({
        label: "Tool Calls",
        value: ((result.input.tool_calls as []) || []).length as ReactNode,
      });
    } else {
      cols.push({
        label: "Role",
        value: result.input.role as ReactNode,
      });
    }

    if (status?.spec.model.model) {
      cols.push({
        label: "Scanning Model",
        value: status.spec.model.model as ReactNode,
      });
    }

    return cols;
  }
};

const messagesCols = (result: ScannerData) => {
  if (result.inputType === "messages") {
    return [
      {
        label: "Message Count",
        value: (result.input as []).length as ReactNode,
      },
    ];
  }
};

const eventCols = (result: ScannerData) => {
  if (result.inputType === "event") {
    return [
      {
        label: "Event Type",
        value: result.input.event as ReactNode,
      },
      {
        label: "Timestamp",
        value: new Date(result.input.timestamp).toLocaleString() as ReactNode,
      },
    ];
  }
};

const eventsCols = (result: ScannerData) => {
  if (result.inputType === "events") {
    return [
      {
        label: "Event Count",
        value: (result.input as []).length as ReactNode,
      },
    ];
  }
};
