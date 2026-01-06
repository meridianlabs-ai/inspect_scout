import clsx from "clsx";
import { FC } from "react";

import { RecordTree } from "../components/content/RecordTree";

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
  return (
    <RecordTree
      id={id}
      record={json}
      className={clsx(styles.jsonMessage, className)}
      useBorders={false}
    />
  );
};
