import { FC } from "react";

import { ErrorPanel } from "../../components/ErrorPanel";
import { useStore } from "../../state/store";
import { TranscriptsNavbar } from "../components/TranscriptsNavbar";
import { useServerTranscripts } from "../server/hooks";

import { TranscriptsList } from "./TranscriptsList";

export const TranscriptsPanel: FC = () => {
  useServerTranscripts();
  const transcripts = useStore((state) => state.transcripts);
  const error = useStore((state) => state.scopedErrors["transcripts"]);

  return (
    <>
      <TranscriptsNavbar bordered={true} />
      {error && (
        <ErrorPanel
          title="Error Loading Transcript"
          error={{ message: error }}
        />
      )}
      {!error && <TranscriptsList transcripts={transcripts} />}
    </>
  );
};
