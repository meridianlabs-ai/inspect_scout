import { ScanResultSummary } from "../types";

export interface IdentifierInfo {
  id: string;
  secondaryId?: string;
  epoch?: string;
}

export const resultIdentifierStr = (
  summary?: ScanResultSummary
): string | undefined => {
  const identifier = resultIdentifier(summary);
  if (!identifier) {
    return undefined;
  }
  if (identifier.secondaryId || identifier.epoch) {
    const result: string[] = [identifier.id];
    if (identifier.secondaryId) {
      result.push(identifier.secondaryId);
    }
    if (identifier.epoch) {
      result.push(identifier.epoch);
    }
    return result.join(" ");
  }
};

export const resultIdentifier = (
  summary?: ScanResultSummary
): IdentifierInfo => {
  if (!summary) {
    return {
      id: "unknown",
    };
  }
  if (summary.inputType === "transcript") {
    // Look in the metadata for a sample identifier
    const sampleIdentifier = getSampleIdentifier(summary);
    if (sampleIdentifier) {
      return sampleIdentifier;
    }
  } else if (summary.inputType === "message") {
    const sampleIdentifier = getSampleIdentifier(summary);
    return {
      id: summary.transcriptSourceId,
      secondaryId: sampleIdentifier ? sampleIdentifier.id : undefined,
      epoch: sampleIdentifier ? sampleIdentifier.epoch : undefined,
    };
  } else if (summary.inputType === "event") {
    const sampleIdentifier = getSampleIdentifier(summary);
    return {
      id: summary.transcriptSourceId,
      secondaryId: sampleIdentifier ? sampleIdentifier.id : undefined,
      epoch: sampleIdentifier ? sampleIdentifier.epoch : undefined,
    };
  }

  return {
    id: summary.transcriptSourceId,
  };
};

const getSampleIdentifier = (
  summary: ScanResultSummary
): { id: string; epoch: string } | undefined => {
  if (summary.transcriptMetadata["id"] && summary.transcriptMetadata["epoch"]) {
    const id = String(summary.transcriptMetadata["id"]);
    const epoch = String(summary.transcriptMetadata["epoch"]);
    return {
      id,
      epoch,
    };
  }
  return undefined;
};

export const resultLog = (summary: ScanResultSummary): string | undefined => {
  if (summary.inputType === "transcript") {
    return summary.transcriptMetadata["log"] as string;
  }
  return undefined;
};
