import clsx from "clsx";
import { FC, ReactNode } from "react";

import { ScannerCore } from "../types";
import { resultIdentifier } from "../utils/results";

import styles from "./Identifier.module.css";

interface IndentifierProps {
  result: ScannerCore;
}

export const Identifier: FC<IndentifierProps> = ({ result }): ReactNode => {
  const identifier = resultIdentifier(result);
  if (identifier.epoch) {
    const id = identifier.id;
    const epoch = identifier.epoch;
    return (
      <div className={clsx(styles.id)}>
        <div>{id}</div>
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
