import clsx from "clsx";
import { FC } from "react";

import styles from "./TranscriptsPanel.module.css";
import { Navbar } from "../components/Navbar";

export const TranscriptsPanel: FC = () => {
  return (
    <>
      <Navbar bordered={true} left={"Transcripts"} />
      <div className={clsx(styles.content)}>Transcripts go here</div>
    </>
  );
};
