import {
  VscodeOption,
  VscodeSingleSelect,
} from "@vscode-elements/react-elements";
import { ChangeEvent, FC, useMemo } from "react";

import { ApplicationIcons } from "../../../components/icons";
import { TextInput } from "../../../components/TextInput";
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

  const handleSearchChange = (e: ChangeEvent<HTMLInputElement>) => {
    onSearchTextChange(e.target.value || undefined);
  };

  return (
    <div className={styles.container}>
      {/* Search first */}
      <TextInput
        icon={ApplicationIcons.search}
        value={searchText ?? ""}
        onChange={handleSearchChange}
        placeholder="Search..."
        className={styles.searchInput}
      />

      {/* Filter second */}
      <div className={styles.filterGroup}>
        <span className={styles.filterLabel}>Split:</span>
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
    </div>
  );
};
