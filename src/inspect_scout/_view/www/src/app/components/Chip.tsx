import clsx from "clsx";
import { FC } from "react";

import { ApplicationIcons } from "../../components/icons";

import styles from "./Chip.module.css";

interface ChipProps {
  icon?: string;
  label?: string;
  value: string;
  title?: string;
  onClick?: () => void;
  onClose?: () => void;
  className?: string | string[];
}

export const Chip: FC<ChipProps> = ({
  icon,
  label,
  value,
  title,
  onClick,
  onClose,
  className,
}) => {
  return (
    <div
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
          className={clsx(styles.label, onClick ? styles.clickable : undefined)}
        >
          {label}
        </span>
      ) : undefined}
      <span
        className={clsx(styles.valueonClick ? styles.clickable : undefined)}
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
          onClick={onClose}
        />
      ) : undefined}
    </div>
  );
};
