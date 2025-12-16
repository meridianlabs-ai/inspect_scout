import { FC } from "react";

import { TranscriptsNavbar } from "../components/TranscriptsNavbar";
import { TranscriptsList } from "./TranscriptsList";

export const TranscriptsPanel: FC = () => {
  return (
    <>
      <TranscriptsNavbar bordered={true} />
      <TranscriptsList />
    </>
  );
};
