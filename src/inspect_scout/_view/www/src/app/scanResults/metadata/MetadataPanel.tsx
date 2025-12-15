import clsx from "clsx";
import { FC } from "react";

import { Card, CardBody } from "../../../components/Card";
import { LabeledValue } from "../../../components/LabeledValue";
import { NoContentsPanel } from "../../../components/NoContentsPanel";
import { RecordTree } from "../../../content/RecordTree";
import { ScanResultData } from "../../types";

import styles from "./Metadata.module.css";

interface MetadataPanelProps {
  resultData?: ScanResultData;
}

export const MetadataPanel: FC<MetadataPanelProps> = ({ resultData }) => {
  const hasMetadata =
    resultData && Object.keys(resultData?.metadata).length > 0;
  return (
    resultData && (
      <div className={clsx(styles.container, "text-size-base")}>
        {!hasMetadata && <NoContentsPanel text={"No metadata available"} />}
        {hasMetadata && (
          <Card>
            <CardBody>
              <LabeledValue label="Metadata">
                <RecordTree
                  id={`result-metadata-${resultData.uuid}`}
                  record={resultData.metadata || {}}
                />
              </LabeledValue>
            </CardBody>
          </Card>
        )}
      </div>
    )
  );
};
