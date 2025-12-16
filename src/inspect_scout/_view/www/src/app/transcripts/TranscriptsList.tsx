import clsx from "clsx";
import { FC } from "react";

import { useStore } from "../../state/store";

interface TranscriptsListProps {
  className?: string | string[];
}

export const TranscriptsList: FC<TranscriptsListProps> = ({ className }) => {
  const transcriptsDatabasePath = useStore(
    (state) => state.transcriptsDatabasePath
  );

  return (
    <div className={clsx(className)}>
      Transcripts List: {transcriptsDatabasePath}
    </div>
  );
};
