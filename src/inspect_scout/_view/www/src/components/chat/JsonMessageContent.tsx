import clsx from "clsx";
import { FC } from "react";

import { useStore } from "../../state/store";
import { RecordTree } from "../content/RecordTree";

import styles from "./JsonMessageContent.module.css";

export interface JsonMessageContentProps {
  json: any;
  id: string;
  className?: string | string[];
}

export const JsonMessageContent: FC<JsonMessageContentProps> = ({
  id,
  json,
  className,
}) => {
  const displayMode = useStore((state) => state.transcriptState.displayMode);
  if (displayMode === "rendered") {
    return (
      <RecordTree
        id={id}
        record={json}
        className={clsx(styles.jsonMessage, className)}
        useBorders={false}
      />
    );
  } else {
    return (
      <pre className={clsx(styles.jsonMessage, className)}>
        {JSON.stringify(json, null, 2)}
      </pre>
    );
  }
};
