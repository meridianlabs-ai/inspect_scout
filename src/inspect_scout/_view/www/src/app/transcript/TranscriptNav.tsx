import { FC, useMemo } from "react";
import { useSearchParams } from "react-router-dom";

import { useLoggingNavigate } from "../../debugging/navigationDebugging";
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
  const navigate = useLoggingNavigate("TranscriptNav");
  const [searchParams] = useSearchParams();

  // Strip transcript-specific params when navigating to a different transcript.
  // The selected agent and deep-link targets don't carry over.
  const cleanParams = useMemo(() => {
    const next = new URLSearchParams(searchParams);
    next.delete("selected");
    next.delete("event");
    next.delete("message");
    return next;
  }, [searchParams]);

  const handlePrevious = () => {
    if (prevId) {
      void navigate(transcriptRoute(transcriptsDir, prevId, cleanParams));
    }
  };

  const handleNext = () => {
    if (nextId) {
      void navigate(transcriptRoute(transcriptsDir, nextId, cleanParams));
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
