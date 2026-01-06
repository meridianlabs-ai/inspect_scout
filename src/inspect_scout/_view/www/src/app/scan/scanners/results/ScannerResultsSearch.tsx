import { ChangeEvent, FC, useCallback } from "react";

import { ApplicationIcons } from "../../../../components/icons";
import { TextInput } from "../../../../components/TextInput";
import { useStore } from "../../../../state/store";

export const ScannerResultsSearch: FC = () => {
  const scansSearchText = useStore((state) => state.scansSearchText);
  const setScansSearchText = useStore((state) => state.setScansSearchText);

  const handleChange = useCallback((e: ChangeEvent<HTMLInputElement>) => {
    setScansSearchText(e.target.value);
  }, []);

  return (
    <TextInput
      icon={ApplicationIcons.search}
      value={scansSearchText}
      onChange={handleChange}
      placeholder={"Search"}
    />
  );
};
