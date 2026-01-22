import {
  VscodeLabel,
  VscodeOption,
  VscodeSingleSelect,
} from "@vscode-elements/react-elements";
import { FC } from "react";

import { getFilenameFromUri } from "../utils";

import styles from "./ValidationSetSelector.module.css";

interface ValidationSetSelectorProps {
  validationSets: string[];
  selectedUri: string | undefined;
  onSelect: (uri: string | undefined) => void;
  loading?: boolean;
  error?: Error | null;
}

/**
 * Combo box component for selecting validation sets.
 * Designed to be reusable for the future annotation UI.
 */
export const ValidationSetSelector: FC<ValidationSetSelectorProps> = ({
  validationSets,
  selectedUri,
  onSelect,
  loading,
  error,
}) => {
  const handleChange = (e: Event) => {
    const value = (e.target as HTMLSelectElement).value;
    onSelect(value || undefined);
  };

  // Extract display name from URI (last part of path without extension)
  const getDisplayName = (uri: string): string => {
    return getFilenameFromUri(uri, true);
  };

  if (loading) {
    return (
      <div className={styles.container}>
        <VscodeLabel>Validation Set</VscodeLabel>
        <div className={styles.loading}>Loading validation sets...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.container}>
        <VscodeLabel>Validation Set</VscodeLabel>
        <div className={styles.error}>Error: {error.message}</div>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <VscodeLabel>Validation Set</VscodeLabel>
      <VscodeSingleSelect
        value={selectedUri ?? ""}
        onChange={handleChange}
        className={styles.select}
      >
        <VscodeOption value="">Select a validation set...</VscodeOption>
        {validationSets.map((uri) => (
          <VscodeOption key={uri} value={uri}>
            {getDisplayName(uri)}
          </VscodeOption>
        ))}
      </VscodeSingleSelect>
    </div>
  );
};
