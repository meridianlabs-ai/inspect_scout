import clsx from "clsx";
import { FC, ReactNode } from "react";

import { ScanResultSummary } from "../types";
import { resultIdentifier } from "../utils/results";

import styles from "./Identifier.module.css";

interface IndentifierProps {
  summary: ScanResultSummary;
}

export const Identifier: FC<IndentifierProps> = ({ summary }): ReactNode => {
  const identifier = resultIdentifier(summary);
  if (identifier.epoch) {
    const id = identifier.id;
    const epoch = identifier.epoch;
    return (
      <div className={clsx(styles.id)}>
        <div className={clsx(styles.idContainer)}>{id}</div>
        <div className={clsx("text-size-smallest", "text-style-secondary")}>
          {identifier.secondaryId ? `${identifier.secondaryId} ` : ""}epoch{" "}
          {epoch}
        </div>
      </div>
    );
  } else {
    return identifier.id;
  }
};
