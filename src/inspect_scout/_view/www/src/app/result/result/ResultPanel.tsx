import clsx from "clsx";
import { FC } from "react";

import { MarkdownDiv } from "../../../components/MarkdownDiv";
import { ScannerData } from "../../types";
import { Value } from "../../values/Value";

import styles from "./ResultPanel.module.css";

interface ResultPanelProps {
  result?: ScannerData;
}

export const ResultPanel: FC<ResultPanelProps> = ({ result }) => {
  return (
    result && (
      <div className={clsx(styles.container)}>
        <div className={clsx(styles.root)}>
          <div className={clsx("text-size-small")}>
            <div className={clsx("text-style-label", "text-style-secondary")}>
              Explanation
            </div>
            <MarkdownDiv
              markdown={result?.explanation || "No explanation provided."}
            />
          </div>
        </div>

        <div className={clsx(styles.root)}>
          <div className={clsx("text-size-small")}>
            <div className={clsx("text-style-label", "text-style-secondary")}>
              Value
            </div>
            <Value result={result} />
          </div>
        </div>
      </div>
    )
  );
};
