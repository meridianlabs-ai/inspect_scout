import { ScannerCore } from "../types";

export interface IdentifierInfo {
  id: string;
  epoch?: string;
}

export const resultIdentifier = (scannerCore: ScannerCore): IdentifierInfo => {
  if (scannerCore.inputType === "transcript") {
    // Look in the metadata for a sample identifier
    if (
      scannerCore.transcriptMetadata["id"] &&
      scannerCore.transcriptMetadata["epoch"]
    ) {
      const id = String(scannerCore.transcriptMetadata["id"]);
      const epoch = String(scannerCore.transcriptMetadata["epoch"]);
      return {
        id,
        epoch,
      };
    }
  } else {
    return {
      id: scannerCore.transcriptSourceId,
    };
  }
};
