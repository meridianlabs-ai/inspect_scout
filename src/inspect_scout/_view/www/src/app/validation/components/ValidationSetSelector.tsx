import {
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
}

/**
 * Combo box component for selecting validation sets.
 * Designed to be reusable for the future annotation UI.
 */
export const ValidationSetSelector: FC<ValidationSetSelectorProps> = ({
  validationSets,
  selectedUri,
  onSelect,
}) => {
  const handleChange = (e: Event) => {
    const value = (e.target as HTMLSelectElement).value;
    onSelect(value || undefined);
  };

  // Extract display name from URI (last part of path with extension)
  const getDisplayName = (uri: string): string => {
    return getFilenameFromUri(uri);
  };

  return (
    <div className={styles.container}>
      <VscodeSingleSelect
        value={selectedUri ?? ""}
        onChange={handleChange}
        className={styles.select}
      >
        {validationSets.map((uri) => (
          <VscodeOption key={uri} value={uri}>
            {getDisplayName(uri)}
          </VscodeOption>
        ))}
      </VscodeSingleSelect>
    </div>
  );
};
