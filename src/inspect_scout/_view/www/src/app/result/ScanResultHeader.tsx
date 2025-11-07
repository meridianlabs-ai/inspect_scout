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
  const columns: Column[] = [];
  if (result?.inputType === "transcript") {
    columns.push({
      label: "Log",
      value: filename(result.input.metadata.log) as ReactNode,
    });
    columns.push({
      label: "Task",
      value: result.input.metadata.task_name as ReactNode,
    });

    columns.push({
      label: "Sample Id",
      value:
        `${result.input.metadata.id} Epoch ${result.input.metadata.epoch}` as ReactNode,
    });

    columns.push({
      label: "Model",
      value: result.input.metadata.model as ReactNode,
    });
  }

  return (
    <div className={clsx(styles.header, classForCols(columns.length))}>
      {columns.map((col) => {
        return (
          <div
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
          <div className={clsx("text-size-small", styles.value, col.className)}>
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
