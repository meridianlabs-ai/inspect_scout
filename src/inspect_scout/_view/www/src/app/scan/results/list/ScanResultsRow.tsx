import clsx from "clsx";
import { FC } from "react";

import { MarkdownDiv } from "../../../../components/MarkdownDiv";

import styles from "./ScanResultsRow.module.css";
import { ScannerRow } from "./types";

interface ScanResultsRowProps {
  index: number;
  entry: ScannerRow;
}

export const ScanResultsRow: FC<ScanResultsRowProps> = ({ index, entry }) => {
  return (
    <div className={clsx(styles.row)}>
      <div className={clsx(styles.id, "text-size-smaller")}>{entry.id}</div>
      <div className={clsx(styles.explanation, "text-size-smaller")}>
        <MarkdownDiv markdown={entry.explanation} />
      </div>
      <div className={clsx(styles.value, "text-size-smaller")}>
        {entry.value}
      </div>
    </div>
  );
};
