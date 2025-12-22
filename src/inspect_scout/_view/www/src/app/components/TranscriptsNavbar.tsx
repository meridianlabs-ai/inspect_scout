import clsx from "clsx";
import { FC } from "react";

import { EditablePath } from "./EditablePath";
import { Navbar } from "./Navbar";
import styles from "./TranscriptsNavbar.module.css";

interface TranscriptsNavbarProps {
  transcriptDir?: string;
  setTranscriptDir: (path: string) => void;
  bordered?: boolean;
  children?: React.ReactNode;
}

export const TranscriptsNavbar: FC<TranscriptsNavbarProps> = ({
  transcriptDir,
  setTranscriptDir,
  bordered = true,
  children,
}) => {
  const left = (
    <div className={styles.navbarLeft}>
      <div
        className={clsx(
          "text-style-label",
          "text-style-secondary",
          "text-size-smallest",
          styles.label
        )}
      >
        Transcripts
      </div>
      <EditablePath
        path={transcriptDir}
        onPathChanged={setTranscriptDir}
        placeholder="Select Transcripts Folder"
        className={clsx(styles.pathInput, "text-size-smallest")}
      />
    </div>
  );

  return <Navbar bordered={bordered} left={left} right={children} />;
};
