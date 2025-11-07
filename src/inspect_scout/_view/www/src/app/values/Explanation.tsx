import { FC, ReactNode } from "react";

import { MarkdownDiv } from "../../components/MarkdownDiv";
import { ScannerCore } from "../types";

interface ExplanationProps {
  result: ScannerCore;
}

export const Explanation: FC<ExplanationProps> = ({ result }): ReactNode => {
  return <MarkdownDiv markdown={result.explanation} />;
};
