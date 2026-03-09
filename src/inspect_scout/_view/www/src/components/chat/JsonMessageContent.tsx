import clsx from "clsx";
import { FC } from "react";

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
  {
    return (
      <pre
        id={id}
        className={clsx(styles.jsonMessage, className, "language-bash")}
      >
        <code className="sourceCode language-bash">
          {JSON.stringify(json, null, 2)}
        </code>
      </pre>
    );
  }
};
