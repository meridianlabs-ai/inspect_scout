import { FC, ReactNode } from "react";

import { LabeledValue } from "../../../components/LabeledValue";
import { MetaDataGrid } from "../../../content/MetaDataGrid";
import { RecordTree } from "../../../content/RecordTree";
import { ModelUsage, ModelUsage2 } from "../../../types/log";
import { ModelTokenTable } from "../../../usage/ModelTokenTable";
import { ScannerData } from "../../types";

import styles from "./InfoPanel.module.css";
import clsx from "clsx";

interface InfoPanelProps {
  result?: ScannerData;
}

export const InfoPanel: FC<InfoPanelProps> = ({ result }) => {
  const panels: ReactNode[] = [<ScannerInfoPanel result={result} />];
  panels.push(
    <ModelTokenTable
      model_usage={
        result?.scanModelUsage as unknown as ModelUsage2 | ModelUsage
      }
    />
  );

  panels.push(<MetaDataGrid entries={result?.scanMetadata || {}} />);

  return result && <div>{panels}</div>;
};

export const ScannerInfoPanel: FC<InfoPanelProps> = ({ result }) => {
  return (
    <div>
      <div className={clsx(styles.scanInfo)}>
        <LabeledValue label="Name">{result?.scannerName}</LabeledValue>
        <LabeledValue label="File">{result?.scannerFile}</LabeledValue>
        <LabeledValue label="Tokens">{result?.scanTotalTokens}</LabeledValue>
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
