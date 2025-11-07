import { FC, ReactNode } from "react";

import { ScannerCore } from "../types";

interface IndentifierProps {
  result: ScannerCore;
}

export const Identifier: FC<IndentifierProps> = ({ result }): ReactNode => {
  if (result.inputType === "transcript") {
    // Look in the metadata for a sample identifier
    if (result.transcriptMetadata["id"] && result.transcriptMetadata["epoch"]) {
      const id = String(result.transcriptMetadata["id"]);
      const epoch = String(result.transcriptMetadata["epoch"]);
      return `${id} (${epoch})`;
    }
  }
  return result.transcriptSourceId;
};
