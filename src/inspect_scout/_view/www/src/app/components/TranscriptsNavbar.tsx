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
      value={transcriptDir}
      onValueChanged={setTranscriptDir}
      placeholder="Select Transcripts Database"
    />
  );

  return <Navbar bordered={bordered} left={left} right={children} />;
};
