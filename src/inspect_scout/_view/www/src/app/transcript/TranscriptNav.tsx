import { FC } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { transcriptRoute } from "../../router/url";
import { Transcript } from "../../types/api-types";
import { NextPreviousNav } from "../components/NextPreviousNav";
import { TaskName } from "../components/TaskName";

interface TranscriptNavProps {
  transcriptsDir: string;
  transcript?: Transcript;
  prevId?: string;
  nextId?: string;
}

export const TranscriptNav: FC<TranscriptNavProps> = ({
  transcriptsDir,
  transcript,
  prevId,
  nextId,
}) => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

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
