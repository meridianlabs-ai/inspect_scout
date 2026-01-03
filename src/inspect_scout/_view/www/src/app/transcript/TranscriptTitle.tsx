import clsx from "clsx";
import { FC } from "react";

import { Transcript } from "../../types/api-types";

import styles from "./TranscriptTitle.module.css";

interface TranscriptTitleProps {
  transcript: Transcript;
}

export const TranscriptTitle: FC<TranscriptTitleProps> = ({ transcript }) => {
  return (
    <div className={clsx(styles.titleContainer)}>
      {transcript.transcript_id} {transcript.model}
    </div>
  );
};
