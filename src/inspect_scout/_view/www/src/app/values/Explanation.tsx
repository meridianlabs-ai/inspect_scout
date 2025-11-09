import { FC, ReactNode } from "react";

import { MarkdownDivWithReferences } from "../components/MarkdownDivWithReferences";
import { ScannerCore } from "../types";

interface ExplanationProps {
  result: ScannerCore;
}

export const Explanation: FC<ExplanationProps> = ({ result }): ReactNode => {
  return (
    <MarkdownDivWithReferences
      markdown={result.explanation || ""}
      references={[...result.messageReferences, ...result.eventReferences]}
    />
  );
};
