import clsx from "clsx";
import { FC, useMemo } from "react";

import { ChatView } from "../../../chat/ChatView";
import { messagesFromEvents } from "../../../chat/messages";
import { Card, CardBody } from "../../../components/Card";
import { LabeledValue } from "../../../components/LabeledValue";
import { MarkdownDiv } from "../../../components/MarkdownDiv";
import { RecordTree } from "../../../content/RecordTree";
import { ScannerData } from "../../types";
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
  console.log({ messages });

  return (
    result && (
      <div className={clsx(styles.container, "text-size-base")}>
        <Card>
          <CardBody className={clsx(styles.explanation)}>
            <LabeledValue label="Explanation">
              <MarkdownDiv
                markdown={result?.explanation || "No explanation provided."}
              />
            </LabeledValue>
            <LabeledValue label="Value">
              <Value result={result} />
            </LabeledValue>
          </CardBody>
        </Card>
        {messages.length > 0 && (
          <Card>
            <CardBody>
              <LabeledValue label="Scan Conversation">
                <ChatView
                  numbered={false}
                  messages={messages}
                  id={`scan-result-chat`}
                  toolCallStyle={"compact"}
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
