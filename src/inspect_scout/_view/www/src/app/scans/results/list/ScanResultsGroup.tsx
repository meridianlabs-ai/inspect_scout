import clsx from "clsx";
import { FC } from "react";

import styles from "./ScanResultsGroup.module.css";

interface ScanResultsGroupProps {
  group: string;
}

export const ScanResultGroup: FC<ScanResultsGroupProps> = ({ group }) => {
  return (
    <div className={clsx(styles.row)}>
      <div
        className={clsx(
          styles.label,
          "text-style-secondary",
          "text-size-smallest"
        )}
      >
        {group}
      </div>
    </div>
  );
};
