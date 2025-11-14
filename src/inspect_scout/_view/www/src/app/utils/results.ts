import { ScannerCore } from "../types";

export interface IdentifierInfo {
  id: string;
  secondaryId?: string;
  epoch?: string;
}

export const resultIdentifier = (scannerCore?: ScannerCore): IdentifierInfo => {
  if (!scannerCore) {
    return {
      id: "unknown",
    };
  }
  if (scannerCore.inputType === "transcript") {
    // Look in the metadata for a sample identifier
    const sampleIdentifier = getSampleIdentifier(scannerCore);
    if (sampleIdentifier) {
      return sampleIdentifier;
    }
  } else if (scannerCore.inputType === "message") {
    const sampleIdentifier = getSampleIdentifier(scannerCore);
    return {
      id: scannerCore.input.id || "null",
      secondaryId: sampleIdentifier ? sampleIdentifier.id : undefined,
      epoch: sampleIdentifier ? sampleIdentifier.epoch : undefined,
    };
  } else if (scannerCore.inputType === "event") {
    const sampleIdentifier = getSampleIdentifier(scannerCore);
    return {
      id: scannerCore.input.uuid || "null",
      secondaryId: sampleIdentifier ? sampleIdentifier.id : undefined,
      epoch: sampleIdentifier ? sampleIdentifier.epoch : undefined,
    };
  }

  return {
    id: scannerCore.transcriptSourceId,
  };
};

const getSampleIdentifier = (
  scannerCore: ScannerCore
): { id: string; epoch: string } | undefined => {
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
  return undefined;
};

export const resultLog = (scannerCore: ScannerCore): string | undefined => {
  if (scannerCore.inputType === "transcript") {
    return scannerCore.transcriptMetadata["log"] as string;
  }
  return undefined;
};
