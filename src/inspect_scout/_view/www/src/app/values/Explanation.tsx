import { FC, ReactNode } from "react";

import {
  MarkdownDivWithReferences,
  MarkdownReference,
} from "../../components/MarkdownDivWithReferences";
import { ScannerCore } from "../types";

interface ExplanationProps {
  result?: ScannerCore;
  references?: MarkdownReference[];
  options?: {
    previewRefsOnHover?: boolean;
  };
}

export const Explanation: FC<ExplanationProps> = ({
  result,
  references,
  options,
}): ReactNode => {
  return (
    <MarkdownDivWithReferences
      markdown={result?.explanation || ""}
      references={references}
      options={options}
    />
  );
};
