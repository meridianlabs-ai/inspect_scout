import clsx from "clsx";
import { FC } from "react";

import { Card, CardBody, CardHeader } from "../../../components/Card";
import { LabeledValue } from "../../../components/LabeledValue";
import { RecordTree } from "../../../content/RecordTree";
import { ModelUsage, ModelUsage2 } from "../../../types/log";
import { ModelTokenTable } from "../../../usage/ModelTokenTable";
import { formatNumber } from "../../../utils/format";
import { ScannerData } from "../../types";

import styles from "./InfoPanel.module.css";

interface InfoPanelProps {
  result?: ScannerData;
}

export const InfoPanel: FC<InfoPanelProps> = ({ result }) => {
  return (
    result && (
      <div className={clsx(styles.container)}>
        <Card>
          <CardHeader label="Scanner Info" type="modern" />
          <CardBody>
            <ScannerInfoPanel result={result} />
          </CardBody>
        </Card>
        <Card>
          <CardHeader label="Model Usage" type="modern" />
          <CardBody>
            <ModelTokenTable
              model_usage={
                result?.scanModelUsage as unknown as ModelUsage2 | ModelUsage
              }
            />
          </CardBody>
        </Card>
        {result?.scanMetadata &&
          Object.keys(result.scanMetadata).length > 0 && (
            <Card>
              <CardHeader label="Metadata" type="modern" />
              <CardBody>
                <RecordTree
                  id={`scan-metadata-${result?.uuid}`}
                  record={result?.scanMetadata || {}}
                />
              </CardBody>
            </Card>
          )}
      </div>
    )
  );
};

export const ScannerInfoPanel: FC<InfoPanelProps> = ({ result }) => {
  return (
    <div className={clsx("text-size-small")}>
      <div className={clsx(styles.scanInfo)}>
        <LabeledValue label="Name">{result?.scannerName}</LabeledValue>
        <LabeledValue label="File">{result?.scannerFile}</LabeledValue>
        <LabeledValue label="Tokens">
          {result?.scanTotalTokens ? formatNumber(result.scanTotalTokens) : ""}
        </LabeledValue>
      </div>
      {result?.scanTags && result.scanTags.length > 0 && (
        <LabeledValue label="Tags">
          {(result?.scanTags || []).join(", ")}
        </LabeledValue>
      )}
      {result?.scannerParams &&
        Object.keys(result.scannerParams).length > 0 && (
          <LabeledValue label="Params">
            <RecordTree
              id={`scanner-params-${result?.uuid}`}
              record={result?.scannerParams}
            />
          </LabeledValue>
        )}
    </div>
  );
};
