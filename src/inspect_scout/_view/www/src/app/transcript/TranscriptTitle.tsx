import clsx from "clsx";
import { FC } from "react";

import { Transcript } from "../../types/api-types";
import { formatDateTime, formatNumber, formatTime } from "../../utils/format";
import { HeadingGrid, HeadingValue } from "../components/HeadingGrid";
import { ScoreValue } from "../components/ScoreValue";
import { TaskName } from "../components/TaskName";

import styles from "./TranscriptTitle.module.css";

interface TranscriptTitleProps {
  transcript: Transcript;
}

export const TranscriptTitle: FC<TranscriptTitleProps> = ({ transcript }) => {
  const cols: HeadingValue[] = [
    {
      label: "Transcript",
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

  if (transcript.score) {
    cols.push({
      label: "Score",
      value: <ScoreValue score={transcript.score} />,
    });
  }

  return (
    <HeadingGrid
      headings={cols}
      className={clsx(styles.titleContainer)}
      labelClassName={clsx(
        "text-style-label",
        "text-size-smallestest",
        "text-style-secondary"
      )}
      valueClassName={clsx("text-size-small")}
    />
  );
};
