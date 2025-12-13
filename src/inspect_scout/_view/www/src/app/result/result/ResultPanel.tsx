import clsx from "clsx";
import { FC } from "react";

import { ScannerData } from "../../types";

import { ResultBody } from "./ResultBody";
import styles from "./ResultPanel.module.css";
import { ResultSidebar } from "./ResultSidebar";

interface ResultPanelProps {
  result?: ScannerData;
}

export const ResultPanel: FC<ResultPanelProps> = ({ result }) => {
  return (
    result && (
      <div className={clsx(styles.container, "text-size-base")}>
        <ResultSidebar result={result} />
        <ResultBody result={result} />
      </div>
    )
  );
};
