import clsx from "clsx";
import { forwardRef } from "react";

import { ApplicationIcons } from "../../../components/icons";

import styles from "./ColumnFilterButton.module.css";

export interface ColumnFilterButtonProps {
  columnId: string;
  isActive: boolean;
  onClick: (event: React.MouseEvent<HTMLButtonElement>) => void;
}

export const ColumnFilterButton = forwardRef<
  HTMLButtonElement,
  ColumnFilterButtonProps
>(({ columnId, isActive, onClick }, ref) => {
  return (
    <button
      ref={ref}
      type="button"
      className={clsx(
        styles.filterButton,
        isActive && styles.filterButtonActive
      )}
      onClick={onClick}
      aria-label={`Filter ${columnId}`}
    >
      <i className={ApplicationIcons.filter} />
    </button>
  );
});

ColumnFilterButton.displayName = "ColumnFilterButton";
