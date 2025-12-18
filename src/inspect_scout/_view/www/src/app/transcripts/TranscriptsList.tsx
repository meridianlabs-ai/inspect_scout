import clsx from "clsx";
import { FC } from "react";

import { LabeledValue } from "../../components/LabeledValue";
import { RecordTree } from "../../content/RecordTree";
import { TranscriptInfo } from "../../types";

interface TranscriptsListProps {
  transcripts?: TranscriptInfo[];
  className?: string | string[];
}

export const TranscriptsList: FC<TranscriptsListProps> = ({
  transcripts,
  className,
}) => {
  return (
    <div className={clsx(className)}>
      <LabeledValue
        label="Number of Transcripts"
        layout="row"
        className={"text-size-small"}
      >
        {transcripts?.length?.toString() || "0"}
      </LabeledValue>
      <hr />
      <RecordTree
        record={{ transcripts }}
        id={"record-transcripts"}
        defaultExpandLevel={0}
      />
      <hr />
    </div>
  );
};
