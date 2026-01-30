import clsx from "clsx";
import { forwardRef } from "react";

import { ApplicationIcons } from "../../components/icons";
import { ToolButton } from "../../components/ToolButton";

import styles from "./ColumnsButton.module.css";

export interface ColumnsButtonProps {
  isOpen: boolean;
  onClick: () => void;
  title?: string;
  label?: string;
}

export const ColumnsButton = forwardRef<HTMLButtonElement, ColumnsButtonProps>(
  (
    { isOpen, onClick, title = "Choose columns", label = "Choose columns" },
    ref
  ) => {
    return (
      <ToolButton
        title={title}
        label={label}
        icon={ApplicationIcons.checkbox.checked}
        onClick={onClick}
        latched={isOpen}
        className={clsx("text-size-smallest", styles.button)}
        ref={ref}
      />
    );
  }
);

ColumnsButton.displayName = "ColumnsButton";
