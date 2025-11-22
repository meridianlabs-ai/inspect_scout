import clsx from "clsx";
import { ButtonHTMLAttributes, forwardRef, ReactNode } from "react";

import styles from "./ToolButton.module.css";

interface ToolButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  label: string | ReactNode;
  icon?: string;
  latched?: boolean;
}

export const ToolButton = forwardRef<HTMLButtonElement, ToolButtonProps>(
  ({ label, icon, className, latched, ...rest }, ref) => {
    // Combine class names, ensuring default classes are applied first

    return (
      <button
        ref={ref}
        type="button"
        className={clsx(
          styles.toolButton,
          "btn",
          "btn-tools",
          className,
          latched ? styles.latched : undefined
        )}
        {...rest}
      >
        {icon && <i className={`${icon}`} />}
        {label}
      </button>
    );
  }
);

// Add display name for debugging purposes
ToolButton.displayName = "ToolButton";
