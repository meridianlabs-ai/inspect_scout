import clsx from "clsx";
import { FC } from "react";

import styles from "./ColumnHeader.module.css";

interface ColumnHeaderProps {
  label?: string;
}

export const ColumnHeader: FC<ColumnHeaderProps> = ({ label }) => {
  return (
    <div className={clsx(styles.header)}>
      <div
        className={clsx(
          styles.label,
          "text-size-smallest",
          "text-style-label",
          "text-style-secondary"
        )}
      >
        {label}
      </div>
    </div>
  );
};
