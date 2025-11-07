import clsx from "clsx";
import { FC } from "react";

import { Card, CardBody, CardHeader } from "../../../components/Card";
import { RecordTree } from "../../../content/RecordTree";
import { ScannerData } from "../../types";

import styles from "./ResultPanel.module.css";
import { MarkdownDiv } from "../../../components/MarkdownDiv";

interface ResultPanelProps {
  result?: ScannerData;
}

export const ResultPanel: FC<ResultPanelProps> = ({ result }) => {
  return (
    result && (
      <div className={clsx(styles.root)}>
        <Card>
          <CardHeader label="Result" />
          <CardBody>
            <MarkdownDiv
              markdown={result?.explanation || "No explanation provided."}
            />

            <RecordTree
              record={result as unknown as Record<string, unknown>}
              id={"results-tree"}
            />
          </CardBody>
        </Card>
      </div>
    )
  );
};
