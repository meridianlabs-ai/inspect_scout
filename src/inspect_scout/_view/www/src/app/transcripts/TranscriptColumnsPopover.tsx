import { FC, useCallback, useMemo } from "react";

import { useStore } from "../../state/store";
import { TranscriptInfo } from "../../types/api-types";
import { ColumnsPopover, ColumnInfo } from "../components/ColumnsPopover";

import {
  COLUMN_HEADER_TITLES,
  COLUMN_LABELS,
  DEFAULT_COLUMN_ORDER,
  DEFAULT_VISIBLE_COLUMNS,
} from "./columns";

export interface TranscriptColumnsPopoverProps {
  positionEl: HTMLElement | null;
  isOpen: boolean;
  setIsOpen: (open: boolean) => void;
}

// Build column info from transcript column definitions
const TRANSCRIPT_COLUMNS: ColumnInfo[] = DEFAULT_COLUMN_ORDER.map(
  (columnId) => ({
    id: columnId,
    label: COLUMN_LABELS[columnId],
    headerTitle: COLUMN_HEADER_TITLES[columnId],
  })
);

export const TranscriptColumnsPopover: FC<TranscriptColumnsPopoverProps> = ({
  positionEl,
  isOpen,
  setIsOpen,
}) => {
  const visibleColumns =
    useStore((state) => state.transcriptsTableState.visibleColumns) ??
    DEFAULT_VISIBLE_COLUMNS;
  const setTableState = useStore((state) => state.setTranscriptsTableState);

  const handleVisibleColumnsChange = useCallback(
    (columns: string[]) => {
      setTableState((prev) => ({
        ...prev,
        visibleColumns: columns as Array<keyof TranscriptInfo>,
      }));
    },
    [setTableState]
  );

  // Convert typed array to string array for the generic component
  const visibleColumnIds = useMemo(
    () => visibleColumns as string[],
    [visibleColumns]
  );

  const defaultVisibleColumnIds = useMemo(
    () => DEFAULT_VISIBLE_COLUMNS as string[],
    []
  );

  return (
    <ColumnsPopover
      positionEl={positionEl}
      isOpen={isOpen}
      setIsOpen={setIsOpen}
      columns={TRANSCRIPT_COLUMNS}
      visibleColumns={visibleColumnIds}
      defaultVisibleColumns={defaultVisibleColumnIds}
      onVisibleColumnsChange={handleVisibleColumnsChange}
      popoverId="transcript-choose-columns-popover"
    />
  );
};
