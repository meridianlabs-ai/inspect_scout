import clsx from "clsx";
import { FC } from "react";

import { MarkdownDiv } from "../../../components/MarkdownDiv";
import { RecordTree } from "../../../content/RecordTree";
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
        <div className={clsx(styles.labeled)}>
          <div className={clsx("text-size-small")}>
            <div className={clsx("text-style-label", "text-style-secondary")}>
              Explanation
            </div>
            <MarkdownDiv
              markdown={result?.explanation || "No explanation provided."}
            />
          </div>
        </div>
        <div className={clsx(styles.labeled)}>
          <div className={clsx("text-size-small")}>
            <div className={clsx("text-style-label", "text-style-secondary")}>
              Value
            </div>
            <Value result={result} />
          </div>
        </div>
        {result.metadata && Object.keys(result.metadata).length > 0 && (
          <div className={clsx(styles.colspan)}>
            <div className={clsx(styles.labeled)}>
              <div className={clsx("text-size-small")}>
                <div
                  className={clsx("text-style-label", "text-style-secondary")}
                >
                  Metadata
                </div>
                <RecordTree
                  id={`result-metadata-${result.uuid}`}
                  record={result.metadata || {}}
                />
              </div>
            </div>
          </div>
        )}
      </div>
    )
  );
};
