import clsx from "clsx";
import { forwardRef } from "react";

import { ApplicationIcons } from "../../components/icons";

import styles from "./Chip.module.css";

interface ChipProps {
  icon?: string;
  label?: string;
  value: string;
  title?: string;
  onClick?: () => void;
  onClose?: (event?: React.MouseEvent | React.KeyboardEvent) => void;
  className?: string | string[];
}

export const Chip = forwardRef<HTMLDivElement, ChipProps>(
  ({ icon, label, value, title, onClick, onClose, className }, ref) => {
    return (
      <div
        ref={ref}
        className={clsx(styles.chip, className)}
        onClick={onClick}
        title={title}
      >
        {icon ? (
          <i
            className={clsx(
              icon,
              styles.icon,
              onClick ? styles.clickable : undefined
            )}
          />
        ) : undefined}
        {label ? (
          <span
            className={clsx(
              styles.label,
              onClick ? styles.clickable : undefined
            )}
          >
            {label}
          </span>
        ) : undefined}
        <span
          className={clsx(styles.value, onClick ? styles.clickable : undefined)}
        >
          {value}
        </span>
        {onClose ? (
          <i
            className={clsx(
              ApplicationIcons.xLarge,
              styles.closeIcon,
              styles.clickable
            )}
            onClick={(event) => {
              event.stopPropagation();
              onClose(event);
            }}
          />
        ) : undefined}
      </div>
    );
  }
);

Chip.displayName = "Chip";
