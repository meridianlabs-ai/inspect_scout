import clsx from "clsx";
import { CSSProperties, FC, ReactNode } from "react";

import styles from "./LabeledValue.module.css";

interface LabeledValueProps {
  label: string;
  style?: CSSProperties;
  valueStyle?: CSSProperties;
  layout?: "column" | "row";
  children: ReactNode;
  className?: string | string[];
}

export const LabeledValue: FC<LabeledValueProps> = ({
  layout = "column",
  style,
  label,
  children,
  valueStyle,
  className,
}) => {
  return (
    <div
      className={clsx(
        styles.labeledValue,
        layout === "column" ? styles.column : styles.row,
        className
      )}
      style={{
        ...style,
      }}
    >
      <div
        className={clsx(
          styles.labeledValueLabel,
          "text-style-label",
          "text-style-secondary"
        )}
      >
        {label}
      </div>
      <div className={clsx(styles.labeledValueValue)} style={{ ...valueStyle }}>
        {children}
      </div>
    </div>
  );
};
