import { FC } from "react";

import { Transcript } from "../../types/api-types";

interface TranscriptTitleProps {
  transcript: Transcript;
}

export const TranscriptTitle: FC<TranscriptTitleProps> = ({ transcript }) => {
  return <div>{transcript.transcript_id}</div>;
};
