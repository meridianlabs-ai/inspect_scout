import clsx from "clsx";
import { FC } from "react";

import styles from "./ScannerResultsGroup.module.css";

interface ScannerResultsGroupProps {
  group: string;
}

export const ScannerResultsGroup: FC<ScannerResultsGroupProps> = ({
  group,
}) => {
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
