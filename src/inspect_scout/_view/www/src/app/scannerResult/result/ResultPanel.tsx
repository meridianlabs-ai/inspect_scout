import clsx from "clsx";
import { FC } from "react";

import { ScanResultData, ScanResultInputData } from "../../types";
import { ValidationCaseEditor } from "../../validation/components/ValidationCaseEditor";

import { ResultBody } from "./ResultBody";
import styles from "./ResultPanel.module.css";
import { ResultSidebar } from "./ResultSidebar";

interface ResultPanelProps {
  resultData: ScanResultData;
  inputData: ScanResultInputData | undefined;
  transcriptId: string | undefined;
  showValidationSidebar?: boolean;
}

export const ResultPanel: FC<ResultPanelProps> = ({
  resultData,
  inputData,
  transcriptId,
  showValidationSidebar = false,
}) => (
  <div
    className={clsx(
      styles.container,
      showValidationSidebar && styles.withValidation,
      "text-size-base"
    )}
  >
    <ResultSidebar resultData={resultData} />
    {inputData ? (
      <ResultBody resultData={resultData} inputData={inputData} />
    ) : (
      <div>No Input Available</div>
    )}
    {showValidationSidebar && transcriptId && (
      <div className={styles.validationSidebar}>
        <ValidationCaseEditor transcriptId={transcriptId} />
      </div>
    )}
  </div>
);
