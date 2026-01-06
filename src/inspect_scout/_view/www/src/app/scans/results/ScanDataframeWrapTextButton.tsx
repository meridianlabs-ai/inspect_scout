import { FC, useCallback } from "react";

import { ApplicationIcons } from "../../../components/icons";
import { useStore } from "../../../state/store";
import { ToolButton } from "../../components/ToolButton";

export const ScanDataframeWrapTextButton: FC = () => {
  const wrapText = useStore((state) => state.dataframeWrapText);
  const setWrapText = useStore((state) => state.setDataframeWrapText);

  const toggleWrapText = useCallback(() => {
    setWrapText(!wrapText);
  }, [wrapText, setWrapText]);

  return (
    <ToolButton
      icon={ApplicationIcons.wrap}
      label="Wrap Text"
      onClick={toggleWrapText}
      latched={wrapText}
    />
  );
};
