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
}

export const Chip: FC<ChipProps> = ({
  icon,
  label,
  value,
  title,
  onClick,
  onClose,
}) => {
  return (
    <div className={styles.chip} onClick={onClick} title={title}>
      {icon ? <i className={icon} /> : undefined}
      {label ? <span className={styles.label}>{label}:</span> : undefined}
      {value}
      {onClose ? (
        <i className={ApplicationIcons.close} onClick={onClose} />
      ) : undefined}
    </div>
  );
};
