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
  const transcripts = useStore((state) => state.transcripts);

  return (
    <div className={clsx(className)}>
      <div>Transcripts List: {transcriptsDatabasePath}</div>
      <hr />
      {transcripts?.map((t) => {
        return <div>{JSON.stringify(t)}</div>;
      })}
      <hr />
    </div>
  );
};
