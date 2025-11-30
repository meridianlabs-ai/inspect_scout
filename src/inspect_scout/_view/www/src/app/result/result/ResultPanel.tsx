import clsx from "clsx";
import { FC, useMemo } from "react";

import { ChatView } from "../../../chat/ChatView";
import { messagesFromEvents } from "../../../chat/messages";
import { Card, CardBody } from "../../../components/Card";
import { LabeledValue } from "../../../components/LabeledValue";
import { MetaDataGrid } from "../../../content/MetaDataGrid";
import { RecordTree } from "../../../content/RecordTree";
import { ScannerData } from "../../types";
import { Explanation } from "../../values/Explanation";
import { ValidationResult } from "../../values/ValidationResult";
import { Value } from "../../values/Value";

import styles from "./ResultPanel.module.css";

interface ResultPanelProps {
  result?: ScannerData;
}

export const ResultPanel: FC<ResultPanelProps> = ({ result }) => {
  const messages = useMemo(() => {
    if (result && result.scanEvents && result.scanEvents.length > 0) {
      return messagesFromEvents(result.scanEvents);
    }
    return [];
  }, [result?.scanEvents]);

  return (
    result && (
      <div className={clsx(styles.container, "text-size-base")}>
        <Card>
          <CardBody className={clsx(styles.explanation)}>
            {result.label && (
              <>
                <div
                  className={clsx("text-style-label", "text-style-secondary")}
                >
                  Label
                </div>
                <div>{result.label}</div>
              </>
            )}
            <div className={clsx("text-style-label", "text-style-secondary")}>
              Value
            </div>
            <div className={clsx(styles.values)}>
              {result.valueType === "object" ? (
                <MetaDataGrid
                  entries={result.value as Record<string, unknown>}
                />
              ) : (
                <Value result={result} style="block" />
              )}
              {result.validationResult !== undefined ? (
                <ValidationResult result={result.validationResult} />
              ) : undefined}
            </div>
            <div className={clsx("text-style-label", "text-style-secondary")}>
              Explanation
            </div>
            <div>
              <Explanation result={result} />
            </div>
            {result.metadata && Object.keys(result.metadata).length > 0 && (
              <>
                <div
                  className={clsx("text-style-label", "text-style-secondary")}
                >
                  Metadata
                </div>
                <div>
                  <MetaDataGrid entries={result.metadata} />
                </div>
              </>
            )}
          </CardBody>
        </Card>
        {messages.length > 0 && (
          <Card>
            <CardBody>
              <LabeledValue label="Scanner">
                <ChatView
                  showLabels={false}
                  messages={messages}
                  id={`scan-result-chat`}
                  toolCallStyle={"complete"}
                  indented={false}
                />
              </LabeledValue>
            </CardBody>
          </Card>
        )}

        {result.metadata && Object.keys(result.metadata).length > 0 && (
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
