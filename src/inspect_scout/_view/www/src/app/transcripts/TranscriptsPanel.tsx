import { FC } from "react";

import { TranscriptsNavbar } from "../components/TranscriptsNavbar";
import { useServerTranscripts } from "../server/hooks";

import { TranscriptsList } from "./TranscriptsList";

export const TranscriptsPanel: FC = () => {
  useServerTranscripts();

  return (
    <>
      <TranscriptsNavbar bordered={true} />
      <TranscriptsList />
    </>
  );
};
