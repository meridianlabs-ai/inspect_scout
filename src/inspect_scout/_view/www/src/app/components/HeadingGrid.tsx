import clsx from "clsx";
import { FC, ReactNode } from "react";

import styles from "./HeadingGrid.module.css";

export interface HeadingValue {
  label: ReactNode;
  value: ReactNode;
  labelPosition?: "left" | "right" | "above" | "below";
  minWidth?: string;
}

interface HeadingGridProps {
  headings: HeadingValue[];
  className?: string | string[];
  labelClassName?: string | string[];
  valueClassName?: string | string[];
}

export const HeadingGrid: FC<HeadingGridProps> = ({
  headings,
  className,
  labelClassName,
  valueClassName,
}) => {
  return (
    <div className={clsx(styles.headingGrid, className)}>
      {headings.map((heading, index) => (
        <HeadingCell
          key={index}
          heading={heading}
          labelClassName={labelClassName}
          valueClassName={valueClassName}
        />
      ))}
    </div>
  );
};

interface HeadingCellProps {
  heading: HeadingValue;
  labelClassName?: string | string[];
  valueClassName?: string | string[];
}

const HeadingCell: FC<HeadingCellProps> = ({
  heading,
  labelClassName,
  valueClassName,
}) => {
  const { label, value, labelPosition = "above", minWidth } = heading;
  const cellStyle = minWidth ? { minWidth } : undefined;

  // Render based on label position
  switch (labelPosition) {
    case "left":
      return (
        <div
          className={clsx(styles.headingCell, styles.horizontal)}
          style={cellStyle}
        >
          <span className={clsx(styles.label, labelClassName)}>{label}</span>
          <span className={clsx(styles.value, valueClassName)}>{value}</span>
        </div>
      );
    case "right":
      return (
        <div
          className={clsx(styles.headingCell, styles.horizontal)}
          style={cellStyle}
        >
          <span className={clsx(styles.value, valueClassName)}>{value}</span>
          <span className={clsx(styles.label, labelClassName)}>{label}</span>
        </div>
      );
    case "above":
      return (
        <div
          className={clsx(styles.headingCell, styles.vertical)}
          style={cellStyle}
        >
          <span className={clsx(styles.label, labelClassName)}>{label}</span>
          <span className={clsx(styles.value, valueClassName)}>{value}</span>
        </div>
      );
    case "below":
      return (
        <div
          className={clsx(styles.headingCell, styles.vertical)}
          style={cellStyle}
        >
          <span className={clsx(styles.value, valueClassName)}>{value}</span>
          <span className={clsx(styles.label, labelClassName)}>{label}</span>
        </div>
      );
  }
};
