import { clsx } from "clsx";
import { FC } from "react";

import styles from "./ChipGroup.module.css";

interface ChipGroupProps {
  className?: string | string[];
  children: React.ReactNode;
}

export const ChipGroup: FC<ChipGroupProps> = ({ className, children }) => {
  return <div className={clsx(styles.chipGroup, className)}>{children}</div>;
};
