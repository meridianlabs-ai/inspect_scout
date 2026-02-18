import clsx from "clsx";
import { FC } from "react";

import styles from "./TimelinePills.module.css";

interface TimelinePillsProps {
  /** Available timeline views. */
  timelines: ReadonlyArray<{ name: string; description: string }>;
  /** Index of the active timeline. */
  activeIndex: number;
  /** Called when a pill is clicked. */
  onSelect: (index: number) => void;
}

export const TimelinePills: FC<TimelinePillsProps> = ({
  timelines,
  activeIndex,
  onSelect,
}) => {
  if (timelines.length <= 1) return null;

  return (
    <div className={styles.pillRow}>
      {timelines.map((tl, i) => (
        <button
          key={i}
          className={clsx(styles.pill, i === activeIndex && styles.pillActive)}
          onClick={() => onSelect(i)}
          title={tl.description}
        >
          {tl.name}
        </button>
      ))}
    </div>
  );
};
