import clsx from "clsx";
import { FC, ReactNode } from "react";

import { filename } from "../../utils/path";
import { ScannerData } from "../types";

import styles from "./ScanResultHeader.module.css";

interface ScanResultHeaderProps {
  result?: ScannerData;
}

interface Column {
  label: string;
  value: ReactNode;
  className?: string | string[];
}

export const ScanResultHeader: FC<ScanResultHeaderProps> = ({ result }) => {
  const columns = colsForResult(result);
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
            : styles.fiveCol
  );
};

const colsForResult: (result?: ScannerData) => Column[] | undefined = (
  result
) => {
  if (!result) {
    return [];
  }
  if (result.inputType === "transcript") {
    return transcriptCols(result);
  } else if (result.inputType === "message") {
    return messageCols(result);
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

const transcriptCols = (result: ScannerData) => {
  if (result.inputType === "transcript") {
    return [
      {
        label: "Log",
        value: filename(result.input.metadata.log) as ReactNode,
      },
      {
        label: "Task",
        value: result.input.metadata.task_name as ReactNode,
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
  }
};

const messageCols = (result: ScannerData) => {
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
