import { FC, useCallback } from "react";

import { ApplicationIcons } from "../../../../components/icons";
import { ToolButton } from "../../../../components/ToolButton";
import { useStore } from "../../../../state/store";

export const ScannerDataframeWrapTextButton: FC = () => {
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
