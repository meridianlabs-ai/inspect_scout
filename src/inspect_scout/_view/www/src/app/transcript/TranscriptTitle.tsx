import clsx from "clsx";
import { FC } from "react";

import { CopyButton } from "../../components/CopyButton";
import { Transcript } from "../../types/api-types";
import { formatDateTime, formatNumber, formatTime } from "../../utils/format";
import { isRecord } from "../../utils/type";
import { HeadingGrid, HeadingValue } from "../components/HeadingGrid";
import { ScoreValue } from "../components/ScoreValue";
import { TaskName } from "../components/TaskName";

import styles from "./TranscriptTitle.module.css";

interface TranscriptTitleProps {
  transcript: Transcript;
}

const labelClassName = clsx(
  "text-style-label",
  "text-size-smallestest",
  "text-style-secondary"
);
const valueClassName = clsx("text-size-small");

export const TranscriptTitle: FC<TranscriptTitleProps> = ({ transcript }) => {
  const cols: HeadingValue[] = [
    {
      label: (
        <>
          Transcript —{" "}
          <span className={styles.transcriptId}>
            {transcript.transcript_id}
          </span>
          <CopyButton value={transcript.transcript_id} />
        </>
      ),
      value: (
        <TaskName
          taskId={transcript.task_id}
          taskRepeat={transcript.task_repeat}
          taskSet={transcript.task_set}
        />
      ),
    },
  ];

  if (transcript.date) {
    cols.push({
      label: "Date",
      value: formatDateTime(new Date(transcript.date)),
    });
  }

  if (transcript.agent) {
    cols.push({
      label: "Agent",
      value: transcript.agent,
    });
  }

  if (transcript.model) {
    cols.push({
      label: "Model",
      value: transcript.model,
    });
  }

  if (transcript.limit) {
    cols.push({
      label: "Limit",
      value: transcript.limit,
    });
  }

  if (transcript.error) {
    cols.push({
      label: "Error",
      value: transcript.error,
    });
  }

  if (transcript.total_tokens) {
    cols.push({
      label: "Tokens",
      value: formatNumber(transcript.total_tokens),
    });
  }

  if (transcript.total_time) {
    cols.push({
      label: "Time",
      value: formatTime(transcript.total_time),
    });
  }

  if (transcript.message_count) {
    cols.push({
      label: "Messages",
      value: transcript.message_count.toString(),
    });
  }

  // Tabular scores (objects/dicts) get their own column on the right;
  // simple scores (strings, numbers, arrays) go inline with other headings.
  const tabularScore = transcript.score != null && isRecord(transcript.score);

  if (transcript.score != null && !tabularScore) {
    cols.push({
      label: "Score",
      value: <ScoreValue score={transcript.score} />,
    });
  }

  return (
    <div
      className={clsx(
        styles.titleContainer,
        tabularScore && styles.titleWithScore
      )}
    >
      <HeadingGrid
        headings={cols}
        className={tabularScore ? styles.metadataRegion : undefined}
        labelClassName={labelClassName}
        valueClassName={valueClassName}
      />
      {transcript.score != null && tabularScore && (
        <div className={styles.scoreRegion}>
          <span className={labelClassName}>Score</span>
          <span className={valueClassName}>
            <ScoreValue score={transcript.score} maxRows={5} />
          </span>
        </div>
      )}
    </div>
  );
};
