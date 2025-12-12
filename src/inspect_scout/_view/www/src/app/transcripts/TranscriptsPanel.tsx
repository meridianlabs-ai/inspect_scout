import clsx from "clsx";
import { FC } from "react";

import styles from "./TranscriptsPanel.module.css";

export const TranscriptsPanel: FC = () => {
  return <div className={clsx(styles.content)}>Transcripts go here</div>;
};
