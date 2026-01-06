import clsx from "clsx";
import { FC } from "react";

import { MetaDataGrid } from "../../../components/content/MetaDataGrid";
import { MarkdownReference } from "../../../components/MarkdownDivWithReferences";
import { NoContentsPanel } from "../../../components/NoContentsPanel";
import { Explanation } from "../../components/Explanation";
import { ValidationResult } from "../../components/ValidationResult";
import { Value } from "../../components/Value";
import { useSelectedScanResultInputData } from "../../hooks";
import { ScanResultData } from "../../types";
import { useMarkdownRefs } from "../../utils/refs";

import styles from "./ResultSidebar.module.css";

interface ResultSidebarProps {
  resultData?: ScanResultData;
}

export const ResultSidebar: FC<ResultSidebarProps> = ({ resultData }) => {
  const dfInput = useSelectedScanResultInputData();
  const refs: MarkdownReference[] = useMarkdownRefs(resultData, dfInput.data);

  if (!resultData) {
    return <NoContentsPanel text="No result to display." />;
  }

  return (
    <div className={clsx(styles.sidebar)}>
      <div className={clsx(styles.container, "text-size-base")}>
        {resultData.label && (
          <>
            <div className={clsx("text-style-label", "text-style-secondary")}>
              Label
            </div>
            <div>{resultData.label}</div>
          </>
        )}
        <div className={clsx("text-style-label", "text-style-secondary")}>
          Value
        </div>
        <div
          className={clsx(
            resultData.validationResult !== undefined
              ? styles.values
              : undefined
          )}
        >
          <Value
            summary={resultData}
            style="block"
            maxTableSize={1000}
            interactive={true}
            references={refs}
            options={{ previewRefsOnHover: false }}
          />
          {resultData.validationResult !== undefined ? (
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
              <ValidationResult result={resultData.validationResult} />
            </div>
          ) : undefined}
        </div>
        <div className={clsx(styles.colspan)}>
          <div className={clsx("text-style-label", "text-style-secondary")}>
            Explanation
          </div>
          <Explanation
            summary={resultData}
            references={refs}
            options={{ previewRefsOnHover: false }}
          />
        </div>
        {resultData.metadata && Object.keys(resultData.metadata).length > 0 && (
          <>
            <div className={clsx("text-style-label", "text-style-secondary")}>
              Metadata
            </div>
            <div>
              <MetaDataGrid
                entries={resultData.metadata}
                references={refs}
                options={{ previewRefsOnHover: false }}
              />
            </div>
          </>
        )}
      </div>
    </div>
  );
};
