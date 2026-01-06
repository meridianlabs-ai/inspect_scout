import clsx from "clsx";
import { FC } from "react";

import { useSelectedScanResultInputData } from "../../hooks";
import { ScanResultData } from "../../types";

import { ResultBody } from "./ResultBody";
import styles from "./ResultPanel.module.css";
import { ResultSidebar } from "./ResultSidebar";

interface ResultPanelProps {
  resultData?: ScanResultData;
}

export const ResultPanel: FC<ResultPanelProps> = ({ resultData }) => {
  const dfInput = useSelectedScanResultInputData();

  return (
    resultData && (
      <div className={clsx(styles.container, "text-size-base")}>
        <ResultSidebar resultData={resultData} />
        <ResultBody resultData={resultData} inputData={dfInput.data} />
      </div>
    )
  );
};
