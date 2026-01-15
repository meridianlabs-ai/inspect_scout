import clsx from "clsx";
import { ButtonHTMLAttributes, forwardRef, ReactNode, useState } from "react";

import styles from "./ToolDropdownButton.module.css";

interface ToolDropdownButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  label: string | ReactNode;
  icon?: string;
  items: Record<string, () => void>;
  dropdownAlign?: "left" | "right";
  dropdownClassName?: string | string[];
  subtle?: boolean;
}

export const ToolDropdownButton = forwardRef<
  HTMLButtonElement,
  ToolDropdownButtonProps
>(
  (
    {
      label,
      icon,
      className,
      items,
      dropdownAlign = "left",
      dropdownClassName,
      subtle,
      ...rest
    },
    ref
  ) => {
    const [isOpen, setIsOpen] = useState(false);

    const handleItemClick = (fn: () => void) => {
      fn();
      setIsOpen(false);
    };

    return (
      <div className={clsx(styles.dropdownContainer)}>
        <button
          ref={ref}
          type="button"
          className={clsx(
            "btn",
            "btn-tools",
            styles.toolButton,
            subtle ? styles.bodyColor : undefined,
            className
          )}
          onClick={() => setIsOpen(!isOpen)}
          {...rest}
        >
          {icon && <i className={`${icon}`} />}
          {label}
          <i className={clsx("bi-chevron-down", styles.chevron)} />
        </button>
        {isOpen && (
          <>
            <div className={styles.backdrop} onClick={() => setIsOpen(false)} />
            <div
              className={clsx(
                styles.dropdownMenu,
                dropdownAlign === "right" ? styles.alignRight : undefined,
                dropdownClassName
              )}
            >
              {Object.entries(items).map(([itemLabel, fn]) => (
                <button
                  key={itemLabel}
                  type="button"
                  className={styles.dropdownItem}
                  onClick={() => handleItemClick(fn)}
                >
                  {itemLabel}
                </button>
              ))}
            </div>
          </>
        )}
      </div>
    );
  }
);

ToolDropdownButton.displayName = "ToolDropdownButton";
