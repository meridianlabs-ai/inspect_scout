import {
  VscodeOption,
  VscodeSingleSelect,
  VscodeTextfield,
} from "@vscode-elements/react-elements";
import { FC, useMemo } from "react";

import { ValidationCase } from "../../../types/api-types";
import { extractUniqueSplits } from "../utils";

import styles from "./ValidationFilterBar.module.css";

interface ValidationFilterBarProps {
  cases: ValidationCase[];
  splitFilter: string | undefined;
  onSplitFilterChange: (split: string | undefined) => void;
  searchText: string | undefined;
  onSearchTextChange: (text: string | undefined) => void;
}

/**
 * Filter bar with split dropdown and ID search.
 */
export const ValidationFilterBar: FC<ValidationFilterBarProps> = ({
  cases,
  splitFilter,
  onSplitFilterChange,
  searchText,
  onSearchTextChange,
}) => {
  // Extract unique splits from cases
  const splits = useMemo(() => extractUniqueSplits(cases), [cases]);

  const handleSplitChange = (e: Event) => {
    const value = (e.target as HTMLSelectElement).value;
    onSplitFilterChange(value || undefined);
  };

  const handleSearchInput = (e: Event) => {
    const value = (e.target as HTMLInputElement).value;
    onSearchTextChange(value || undefined);
  };

  return (
    <div className={styles.container}>
      <div className={styles.filterGroup}>
        <VscodeSingleSelect
          value={splitFilter ?? ""}
          onChange={handleSplitChange}
          className={styles.splitSelect}
        >
          <VscodeOption value="">All splits</VscodeOption>
          {splits.map((split) => (
            <VscodeOption key={split} value={split}>
              {split}
            </VscodeOption>
          ))}
        </VscodeSingleSelect>
      </div>

      <div className={styles.searchGroup}>
        <VscodeTextfield
          value={searchText ?? ""}
          onInput={handleSearchInput}
          placeholder="Search by ID..."
          className={styles.searchInput}
        />
      </div>
    </div>
  );
};
