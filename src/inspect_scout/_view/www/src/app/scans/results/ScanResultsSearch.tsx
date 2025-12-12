import { ChangeEvent, FC, useCallback } from "react";

import { TextInput } from "../../../components/TextInput";
import { useStore } from "../../../state/store";
import { ApplicationIcons } from "../../appearance/icons";

export const ScanResultsSearch: FC = () => {
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
