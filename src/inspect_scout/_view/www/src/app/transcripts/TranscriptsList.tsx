import clsx from "clsx";
import { FC } from "react";

import { ErrorPanel } from "../../components/ErrorPanel";
import { LabeledValue } from "../../components/LabeledValue";
import { useStore } from "../../state/store";

interface TranscriptsListProps {
  className?: string | string[];
}

export const TranscriptsList: FC<TranscriptsListProps> = ({ className }) => {
  const transcripts = useStore((state) => state.transcripts);
  const error = useStore((state) => state.scopedErrors["transcripts"]);

  return (
    <div className={clsx(className)}>
      {error && (
        <ErrorPanel
          title="Error Loading Transcript"
          error={{ message: error }}
        />
      )}

      <LabeledValue
        label="Number of Transcripts"
        layout="row"
        className={"text-size-small"}
      >
        {transcripts?.length?.toString() || "0"}
      </LabeledValue>
      <hr />
      {transcripts?.map((t) => {
        return <div>{JSON.stringify(t)}</div>;
      })}
      <hr />
    </div>
  );
};
