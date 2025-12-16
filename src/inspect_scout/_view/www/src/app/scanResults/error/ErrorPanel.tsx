import { clsx } from "clsx";
import { FC } from "react";

import { ANSIDisplay } from "../../../components/AnsiDisplay";
import { Card, CardBody, CardHeader } from "../../../components/Card";

import styles from "./ErrorPanel.module.css";

interface ErrorPanelProps {
  error?: string;
  traceback?: string;
}

export const ErrorPanel: FC<ErrorPanelProps> = ({ error, traceback }) => {
  return (
    <Card className={clsx(styles.container)}>
      <CardHeader type="modern">Error</CardHeader>
      <CardBody>
        <div className={clsx("text-size-smaller")}>{error}</div>

        {traceback && (
          <ANSIDisplay
            className={clsx(styles.traceback, "text-size-smaller")}
            output={traceback}
          />
        )}
      </CardBody>
    </Card>
  );
};
