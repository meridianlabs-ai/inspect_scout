import { FC } from "react";

import { EditableText } from "./EditableText";
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
    <EditableText
      text={transcriptDir || "Select Transcripts Database"}
      onChange={setTranscriptDir}
    />
  );

  return <Navbar bordered={bordered} left={left} right={children} />;
};
