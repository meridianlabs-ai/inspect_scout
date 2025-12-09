import clsx from "clsx";
import { FC } from "react";

import { MarkdownReference } from "../../../components/MarkdownDivWithReferences";
import { NoContentsPanel } from "../../../components/NoContentsPanel";
import { MetaDataGrid } from "../../../content/MetaDataGrid";
import { ScannerData } from "../../types";
import { useMarkdownRefs } from "../../utils/refs";
import { Explanation } from "../../values/Explanation";
import { ValidationResult } from "../../values/ValidationResult";
import { Value } from "../../values/Value";

import styles from "./ResultSidebar.module.css";
interface ResultSidebarProps {
  result?: ScannerData;
}

export const ResultSidebar: FC<ResultSidebarProps> = ({ result }) => {
  const refs: MarkdownReference[] = useMarkdownRefs(result);

  if (!result) {
    return <NoContentsPanel text="No result to display." />;
  }

  return (
    <div className={clsx(styles.sidebar)}>
      <div className={clsx(styles.container, "text-size-base")}>
        {result.label && (
          <>
            <div className={clsx("text-style-label", "text-style-secondary")}>
              Label
            </div>
            <div>{result.label}</div>
          </>
        )}
        <div className={clsx("text-style-label", "text-style-secondary")}>
          Value
        </div>
        <div
          className={clsx(
            result.validationResult !== undefined ? styles.values : undefined
          )}
        >
          <Value
            result={result}
            style="block"
            maxTableSize={1000}
            interactive={true}
            references={refs}
          />
          {result.validationResult !== undefined ? (
            <div className={clsx(styles.validation)}>
              <div
                className={clsx(
                  "text-style-label",
                  "text-style-secondary",
                  "text-size-smallest",
                  styles.validationLabel
                )}
              >
                Validation
              </div>
              <ValidationResult result={result.validationResult} />
            </div>
          ) : undefined}
        </div>
        <div className={clsx(styles.colspan)}>
          <div className={clsx("text-style-label", "text-style-secondary")}>
            Explanation
          </div>
          <Explanation result={result} references={refs} />
        </div>
        {result.metadata && Object.keys(result.metadata).length > 0 && (
          <>
            <div className={clsx("text-style-label", "text-style-secondary")}>
              Metadata
            </div>
            <div>
              <MetaDataGrid entries={result.metadata} references={refs} />
            </div>
          </>
        )}
      </div>
    </div>
  );
};
