import { ChangeEvent, FC, useCallback } from "react";

import { ApplicationIcons } from "../../../../components/icons";
import { TextInput } from "../../../../components/TextInput";
import { useStore } from "../../../../state/store";

import styles from "./ScannerResultsSearch.module.css";

export const ScannerResultsSearch: FC = () => {
  const scansSearchText = useStore((state) => state.scansSearchText);
  const setScansSearchText = useStore((state) => state.setScansSearchText);

  const handleChange = useCallback((e: ChangeEvent<HTMLInputElement>) => {
    setScansSearchText(e.target.value);
    // TODO: lint react-hooks/exhaustive-deps - refactor to avoid the lint
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <TextInput
      icon={ApplicationIcons.search}
      value={scansSearchText}
      onChange={handleChange}
      placeholder={"Search"}
      className={styles.searchBox}
    />
  );
};
