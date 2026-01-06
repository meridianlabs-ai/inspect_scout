import clsx from "clsx";
import { ChangeEvent, FC, useCallback } from "react";

import { useStore } from "../../../../state/store";

import styles from "./ScannerResultsFilter.module.css";

export const kFilterPositiveResults = "positive_results";
export const kFilterAllResults = "all_results";

export const ScannerResultsFilter: FC = () => {
  const setSelectedFilter = useStore((state) => state.setSelectedFilter);
  const selectedFilter = useStore((state) => state.selectedFilter);

  const handleChange = useCallback(
    (e: ChangeEvent<HTMLSelectElement>) => {
      const sel = e.target as HTMLSelectElement;
      setSelectedFilter(sel.value);
    },
    [setSelectedFilter]
  );

  const options = [
    { label: "Positive", val: kFilterPositiveResults },
    { label: "All", val: kFilterAllResults },
  ];

  return (
    <div className={styles.flex}>
      <span
        className={clsx(
          "sort-filter-label",
          "text-size-smaller",
          "text-style-label",
          "text-style-secondary",
          styles.label
        )}
      >
        Results:
      </span>
      <select
        id={"scan-result-filter"}
        className={clsx("form-select", "form-select-sm", "text-size-smaller")}
        aria-label=".sort-filter-label"
        value={selectedFilter}
        onChange={handleChange}
      >
        {options.map((option) => {
          return (
            <option key={option.val} value={option.val}>
              {option.label}
            </option>
          );
        })}
      </select>
    </div>
  );
};
