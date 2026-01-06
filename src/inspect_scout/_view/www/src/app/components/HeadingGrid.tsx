import clsx from "clsx";
import { FC, ReactNode } from "react";

import styles from "./HeadingGrid.module.css";

export interface HeadingValue {
  label: string;
  value: ReactNode;
  labelPosition?: "left" | "right" | "above" | "below";
}

interface HeadingGridProps {
  headings: HeadingValue[];
  rows?: number;
  columns?: number;
  className?: string | string[];
  labelClassName?: string | string[];
  valueClassName?: string | string[];
}

export const HeadingGrid: FC<HeadingGridProps> = ({
  headings,
  rows,
  columns,
  className,
  labelClassName,
  valueClassName,
}) => {
  // Default to 1 row and N columns (where N is the number of headings)
  const actualColumns = columns ?? headings.length;
  const actualRows = rows ?? 1;

  // Calculate the grid size
  const totalCells = actualRows * actualColumns;

  // Pad the headings array if needed or slice if too many
  const gridItems = headings.slice(0, totalCells);

  return (
    <div
      className={clsx(styles.headingGrid, className)}
      style={{
        gridTemplateColumns: `repeat(${actualColumns}, auto)`,
        gridTemplateRows: `repeat(${actualRows}, auto)`,
      }}
    >
      {gridItems.map((heading, index) => (
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
  const { label, value, labelPosition = "above" } = heading;

  // Render based on label position
  switch (labelPosition) {
    case "left":
      return (
        <div className={clsx(styles.headingCell, styles.horizontal)}>
          <span className={clsx(styles.label, labelClassName)}>{label}</span>
          <span className={clsx(styles.value, valueClassName)}>{value}</span>
        </div>
      );
    case "right":
      return (
        <div className={clsx(styles.headingCell, styles.horizontal)}>
          <span className={clsx(styles.value, valueClassName)}>{value}</span>
          <span className={clsx(styles.label, labelClassName)}>{label}</span>
        </div>
      );
    case "above":
      return (
        <div className={clsx(styles.headingCell, styles.vertical)}>
          <span className={clsx(styles.label, labelClassName)}>{label}</span>
          <span className={clsx(styles.value, valueClassName)}>{value}</span>
        </div>
      );
    case "below":
      return (
        <div className={clsx(styles.headingCell, styles.vertical)}>
          <span className={clsx(styles.value, valueClassName)}>{value}</span>
          <span className={clsx(styles.label, labelClassName)}>{label}</span>
        </div>
      );
  }
};
