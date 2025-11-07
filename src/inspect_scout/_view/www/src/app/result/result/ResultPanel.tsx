import clsx from "clsx";
import { FC } from "react";

import { RecordTree } from "../../../content/RecordTree";
import { ScannerData } from "../../types";

import styles from "./ResultPanel.module.css";

interface ResultPanelProps {
  result: ScannerData;
}

export const ResultPanel: FC<ResultPanelProps> = ({ result }) => {
  return (
    result && (
      <div className={clsx(styles.root)}>
        <RecordTree
          record={result as unknown as Record<string, unknown>}
          id={"results-tree"}
        />
      </div>
    )
  );
};
