import { FC, useCallback } from "react";

import { GRID_STATE_NAME } from "../../../components/DataframeView";
import { ApplicationIcons } from "../../../components/icons";
import { useStore } from "../../../state/store";
import { ToolButton } from "../../components/ToolButton";

export const ScanDataframeClearFiltersButton: FC = () => {
  const setGridState = useStore((state) => state.setGridState);
  const gridState = useStore((state) => state.gridStates[GRID_STATE_NAME]);

  const clearState = useCallback(() => {
    const { filter, ...state } = gridState || {};
    setGridState(GRID_STATE_NAME, state);
  }, [gridState, setGridState]);

  return (
    <ToolButton
      icon={ApplicationIcons.filter}
      label="Clear Filters"
      onClick={clearState}
    />
  );
};
