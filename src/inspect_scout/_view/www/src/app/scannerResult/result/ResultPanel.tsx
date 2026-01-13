import clsx from "clsx";
import { FC } from "react";

import { ScanResultData, ScanResultInputData } from "../../types";

import { ResultBody } from "./ResultBody";
import styles from "./ResultPanel.module.css";
import { ResultSidebar } from "./ResultSidebar";

interface ResultPanelProps {
  resultData: ScanResultData;
  inputData: ScanResultInputData | undefined;
}

export const ResultPanel: FC<ResultPanelProps> = ({
  resultData,
  inputData,
}) => (
  <div className={clsx(styles.container, "text-size-base")}>
    <ResultSidebar resultData={resultData} />
    {inputData ? (
      <ResultBody resultData={resultData} inputData={inputData} />
    ) : (
      <div>No Input Available</div>
    )}
  </div>
);
