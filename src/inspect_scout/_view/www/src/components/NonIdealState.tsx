import clsx from "clsx";
import { FC, ReactNode } from "react";

import styles from "./NonIdealState.module.css";

interface NonIdealStateProps {
  icon?: string;
  title: string;
  description?: string;
  action?: ReactNode;
  className?: string;
}

export const NonIdealState: FC<NonIdealStateProps> = ({
  icon,
  title,
  description,
  action,
  className,
}) => {
  return (
    <div className={clsx(styles.container, className)}>
      {icon && <i className={clsx(styles.icon, icon)} />}
      <div className={styles.title}>{title}</div>
      {description && <div className={styles.description}>{description}</div>}
      {action && <div className={styles.action}>{action}</div>}
    </div>
  );
};
