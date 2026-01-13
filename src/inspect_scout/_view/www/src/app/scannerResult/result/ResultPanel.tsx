import clsx from "clsx";
import { FC } from "react";

import { LoadingBar } from "../../../components/LoadingBar";
import { useSelectedScanResultInputData } from "../../hooks/useSelectedScanResultInputData";
import { ScanResultData } from "../../types";

import { ResultBody } from "./ResultBody";
import styles from "./ResultPanel.module.css";
import { ResultSidebar } from "./ResultSidebar";

interface ResultPanelProps {
  resultData: ScanResultData;
}

export const ResultPanel: FC<ResultPanelProps> = ({ resultData }) => {
  const { loading, data: inputData } = useSelectedScanResultInputData();
  // TODO: Code up the error path or confirm the swallowing of the input error

  return (
    <>
      <div className={clsx(styles.container, "text-size-base")}>
        <LoadingBar loading={true} />
        <ResultSidebar resultData={resultData} />
        {inputData ? (
          <ResultBody resultData={resultData} inputData={inputData} />
        ) : (
          <div>No Input Available</div>
        )}
      </div>
    </>
  );
};
