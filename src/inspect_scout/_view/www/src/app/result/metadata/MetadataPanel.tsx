import clsx from "clsx";
import { FC } from "react";

import { Card, CardBody } from "../../../components/Card";
import { LabeledValue } from "../../../components/LabeledValue";
import { NoContentsPanel } from "../../../components/NoContentsPanel";
import { RecordTree } from "../../../content/RecordTree";
import { ScannerData } from "../../types";

import styles from "./Metadata.module.css";

interface MetadataPanelProps {
  result?: ScannerData;
}

export const MetadataPanel: FC<MetadataPanelProps> = ({ result }) => {
  const hasMetadata = result && Object.keys(result?.metadata).length > 0;
  return (
    result && (
      <div className={clsx(styles.container, "text-size-base")}>
        {!hasMetadata && <NoContentsPanel text={"No metadata available"} />}
        {hasMetadata && (
          <Card>
            <CardBody>
              <LabeledValue label="Metadata">
                <RecordTree
                  id={`result-metadata-${result.uuid}`}
                  record={result.metadata || {}}
                />
              </LabeledValue>
            </CardBody>
          </Card>
        )}
      </div>
    )
  );
};
