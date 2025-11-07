import clsx from "clsx";
import { FC } from "react";

import { ScannerData } from "../../types";

import styles from "./ResultPanel.module.css";

interface ResultPanelProps {
  result: ScannerData;
}

export const ResultPanel: FC<ResultPanelProps> = ({ result }) => {
  return (
    <div className={clsx(styles.header)}>
      <div>Id</div>
      <div>Explanation</div>
      <div>Value</div>
      <div></div>
      <div>Explanation</div>
      <div>Value</div>
    </div>
  );
};
