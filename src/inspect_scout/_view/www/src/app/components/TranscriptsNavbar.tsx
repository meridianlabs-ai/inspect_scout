import { FC } from "react";

import { useStore } from "../../state/store";

import { EditableText } from "./EditableText";
import { Navbar } from "./Navbar";

interface TranscriptsNavbarProps {
  transcriptDir?: string;
  bordered?: boolean;
  children?: React.ReactNode;
}

export const TranscriptsNavbar: FC<TranscriptsNavbarProps> = ({
  transcriptDir,
  bordered = true,
  children,
}) => {
  const transcriptsDatabasePath = useStore(
    (state) => state.transcriptsDatabasePath
  );
  const setTranscriptsDatabasePath = useStore(
    (state) => state.setTranscriptsDatabasePath
  );
  const left = (
    <EditableText
      text={
        transcriptsDatabasePath ||
        transcriptDir ||
        "Select Transcripts Database"
      }
      onChange={setTranscriptsDatabasePath}
    />
  );

  return <Navbar bordered={bordered} left={left} right={children} />;
};
