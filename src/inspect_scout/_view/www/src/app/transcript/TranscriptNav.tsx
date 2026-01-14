import { FC, useMemo } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { Condition, SimpleCondition } from "../../query/types";
import { transcriptRoute } from "../../router/url";
import { useStore } from "../../state/store";
import { Transcript } from "../../types/api-types";
import { NextPreviousNav } from "../components/NextPreviousNav";
import { TaskName } from "../components/TaskName";
import { useAdjacentTranscriptIds } from "../server/useAdjacentTranscriptIds";
import { TRANSCRIPTS_INFINITE_SCROLL_CONFIG } from "../transcripts/constants";

interface TranscriptNavProps {
  transcriptId: string;
  transcriptsDir: string;
  transcript?: Transcript;
}

export const TranscriptNav: FC<TranscriptNavProps> = ({
  transcriptId,
  transcriptsDir,
  transcript,
}) => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  // Build filter condition from column filters (same as TranscriptsPanel)
  const columnFilters =
    useStore((state) => state.transcriptsTableState.columnFilters) ?? {};
  const condition = useMemo(() => {
    const filterConditions = Object.values(columnFilters)
      .map((filter) => filter.condition)
      .filter((c): c is SimpleCondition => Boolean(c));
    return filterConditions.reduce<Condition | undefined>(
      (acc, c) => (acc ? acc.and(c) : c),
      undefined
    );
  }, [columnFilters]);

  // Get sorting from store
  const sorting = useStore((state) => state.transcriptsTableState.sorting);

  // Get adjacent transcript IDs
  const adjacentIds = useAdjacentTranscriptIds(
    transcriptId,
    transcriptsDir,
    TRANSCRIPTS_INFINITE_SCROLL_CONFIG.pageSize,
    condition,
    sorting
  );

  const [prevId, nextId] = adjacentIds.data ?? [undefined, undefined];

  const handlePrevious = () => {
    if (prevId) {
      void navigate(transcriptRoute(transcriptsDir, prevId, searchParams));
    }
  };

  const handleNext = () => {
    if (nextId) {
      void navigate(transcriptRoute(transcriptsDir, nextId, searchParams));
    }
  };

  return (
    <NextPreviousNav
      onPrevious={handlePrevious}
      onNext={handleNext}
      hasPrevious={!!prevId}
      hasNext={!!nextId}
    >
      {transcript && (
        <TaskName
          taskId={transcript.task_id}
          taskRepeat={transcript.task_repeat}
          taskSet={transcript.task_set}
        />
      )}
    </NextPreviousNav>
  );
};
