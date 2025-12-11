import { forwardRef, useCallback } from "react";

import { useStore } from "../../../state/store";
import { ApplicationIcons } from "../../appearance/icons";
import { ToolButton } from "../../components/ToolButton";

export const ScanDataframeFilterColumnsButton = forwardRef<
  HTMLButtonElement,
  unknown
>((_, ref) => {
  const showFilter = useStore((state) => state.dataframeShowFilterColumns);
  const setShowFilter = useStore(
    (state) => state.setDataframeShowFilterColumns
  );

  const toggleShowFilter = useCallback(() => {
    setShowFilter(!showFilter);
  }, [showFilter, setShowFilter]);

  return (
    <ToolButton
      icon={ApplicationIcons.checkbox.checked}
      label="Choose Columns"
      onClick={toggleShowFilter}
      latched={showFilter}
      ref={ref}
    />
  );
});
