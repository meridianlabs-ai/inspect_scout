import clsx from "clsx";
import { FC } from "react";

import { Card, CardBody, CardHeader } from "../../../components/Card";
import { LabeledValue } from "../../../components/LabeledValue";
import { RecordTree } from "../../../content/RecordTree";
import { ModelUsage, ModelUsage2 } from "../../../types/log";
import { ModelTokenTable } from "../../../usage/ModelTokenTable";
import { formatNumber } from "../../../utils/format";
import { ScanResultData } from "../../types";

import styles from "./InfoPanel.module.css";

interface InfoPanelProps {
  resultData?: ScanResultData;
}

export const InfoPanel: FC<InfoPanelProps> = ({ resultData }) => {
  return (
    resultData && (
      <div className={clsx(styles.container)}>
        <Card>
          <CardHeader label="Scanner Info" type="modern" />
          <CardBody>
            <ScannerInfoPanel resultData={resultData} />
          </CardBody>
        </Card>
        {resultData?.scanModelUsage &&
          Object.keys(resultData?.scanModelUsage).length > 0 && (
            <Card>
              <CardHeader label="Model Usage" type="modern" />
              <CardBody>
                <ModelTokenTable
                  model_usage={
                    resultData?.scanModelUsage as unknown as
                      | ModelUsage2
                      | ModelUsage
                  }
                />
              </CardBody>
            </Card>
          )}
        {resultData?.scanMetadata &&
          Object.keys(resultData.scanMetadata).length > 0 && (
            <Card>
              <CardHeader label="Metadata" type="modern" />
              <CardBody>
                <RecordTree
                  id={`scan-metadata-${resultData?.uuid}`}
                  record={resultData?.scanMetadata || {}}
                />
              </CardBody>
            </Card>
          )}
      </div>
    )
  );
};

export const ScannerInfoPanel: FC<InfoPanelProps> = ({ resultData }) => {
  return (
    <div className={clsx("text-size-small")}>
      <div className={clsx(styles.scanInfo)}>
        <LabeledValue label="Name">{resultData?.scannerName}</LabeledValue>
        {resultData?.scannerFile && resultData.scannerFile !== null && (
          <LabeledValue label="File">{resultData?.scannerFile}</LabeledValue>
        )}
        {(resultData?.scanTotalTokens || 0) > 0 && (
          <LabeledValue label="Tokens">
            {resultData?.scanTotalTokens
              ? formatNumber(resultData.scanTotalTokens)
              : ""}
          </LabeledValue>
        )}
      </div>
      {resultData?.scanTags && resultData.scanTags.length > 0 && (
        <LabeledValue label="Tags">
          {(resultData?.scanTags || []).join(", ")}
        </LabeledValue>
      )}
      {resultData?.scannerParams &&
        Object.keys(resultData.scannerParams).length > 0 && (
          <LabeledValue label="Params">
            <RecordTree
              id={`scanner-params-${resultData?.uuid}`}
              record={resultData?.scannerParams}
            />
          </LabeledValue>
        )}
    </div>
  );
};
