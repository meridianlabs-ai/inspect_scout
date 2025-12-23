import clsx from "clsx";
import { FC } from "react";

import { ApplicationIcons } from "../appearance/icons";

import { EditablePath } from "./EditablePath";
import { Navbar } from "./Navbar";

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
    <EditablePath
      path={transcriptDir}
      label="Transcripts"
      icon={ApplicationIcons.transcript}
      onPathChanged={setTranscriptDir}
      placeholder="Select Transcripts Folder"
      className="text-size-smallest"
    />
  );

  return <Navbar bordered={bordered} left={left} right={children} />;
};
