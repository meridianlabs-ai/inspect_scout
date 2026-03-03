import clsx from "clsx";
import { FC, useCallback, useState } from "react";

import type { Timeline } from "../../../components/transcript/timeline";

import styles from "./TimelineSelector.module.css";

// =============================================================================
// Types
// =============================================================================

export interface TimelineSelectorProps {
  /** Available timeline views. */
  timelines: ReadonlyArray<Timeline>;
  /** Index of the active timeline. */
  activeIndex: number;
  /** Called when a timeline is selected. */
  onSelect: (index: number) => void;
}

// =============================================================================
// Component
// =============================================================================

export const TimelineSelector: FC<TimelineSelectorProps> = ({
  timelines,
  activeIndex,
  onSelect,
}) => {
  const [isOpen, setIsOpen] = useState(false);

  const handleSelect = useCallback(
    (index: number) => {
      onSelect(index);
      setIsOpen(false);
    },
    [onSelect]
  );

  if (timelines.length <= 1) return null;

  const active = timelines[activeIndex];
  if (!active) return null;

  return (
    <div className={styles.selectorContainer}>
      <button
        type="button"
        className={styles.selectorButton}
        onClick={() => setIsOpen((prev) => !prev)}
        title={active.description}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
      >
        {active.name}
        <i className={clsx("bi-chevron-down", styles.chevron)} />
      </button>
      {isOpen && (
        <>
          <div className={styles.backdrop} onClick={() => setIsOpen(false)} />
          <div className={styles.dropdownMenu} role="listbox">
            {timelines.map((tl, i) => (
              <button
                key={tl.name}
                type="button"
                className={clsx(
                  styles.dropdownItem,
                  i === activeIndex && styles.dropdownItemActive
                )}
                role="option"
                aria-selected={i === activeIndex}
                onClick={() => handleSelect(i)}
              >
                {tl.name}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
};
