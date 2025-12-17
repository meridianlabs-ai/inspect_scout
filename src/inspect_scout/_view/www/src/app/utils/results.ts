import { ScanResultSummary } from "../types";

export interface IdentifierInfo {
  taskSet?: string;
  id: string | number;
  secondaryId?: string | number;
  epoch?: number;
}

export const resultIdentifierStr = (
  summary?: ScanResultSummary
): string | undefined => {
  const identifier = resultIdentifier(summary);
  if (!identifier) {
    return undefined;
  }
  if (identifier.secondaryId || identifier.epoch) {
    const id: string[] = [];
    if (identifier.taskSet) {
      id.push(identifier.taskSet);
    }
    id.push(String(identifier.id));

    const result: string[] = [id.join("/")];
    if (identifier.secondaryId) {
      result.push(String(identifier.secondaryId));
    }
    if (identifier.epoch) {
      result.push(`(${String(identifier.epoch)})`);
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
): IdentifierInfo | undefined => {
  // Read the new ids. The metadata reading is only here to support old
  // scan results that didn't have these fields.
  const id =
    summary.transcriptTaskId ||
    (summary.transcriptMetadata["id"] as string | number);
  const epoch = (summary.transcriptTaskRepeat ||
    summary.transcriptMetadata["epoch"]) as number | undefined;

  if (id && epoch) {
    const taskSet =
      summary.transcriptTaskSet ||
      (summary.transcriptMetadata["task_name"] as string | undefined);
    return {
      id,
      epoch,
      taskSet,
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
