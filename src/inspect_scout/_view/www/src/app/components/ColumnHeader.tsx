import clsx from "clsx";
import { ButtonHTMLAttributes, FC, forwardRef, ReactNode } from "react";

import styles from "./ColumnHeader.module.css";

interface ColumnHeaderProps {
  label?: string;
  actions?: ReactNode;
}

export const ColumnHeader: FC<ColumnHeaderProps> = ({ label, actions }) => {
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
      {actions && <div className={styles.actions}>{actions}</div>}
    </div>
  );
};

interface ColumnHeaderButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  icon: string;
}

export const ColumnHeaderButton = forwardRef<
  HTMLButtonElement,
  ColumnHeaderButtonProps
>(({ icon, className, ...rest }, ref) => {
  return (
    <button
      ref={ref}
      type="button"
      className={clsx(styles.iconButton, className)}
      {...rest}
    >
      <i className={icon} />
    </button>
  );
});

ColumnHeaderButton.displayName = "ColumnHeaderButton";
