import clsx from "clsx";
import { FC, ReactNode } from "react";

import { MarkdownDiv } from "../../../../components/MarkdownDiv";

import styles from "./ScanResultsRow.module.css";
import { ScannerPreview } from "./types";

interface ScanResultsRowProps {
  index: number;
  entry: ScannerPreview;
}

export const ScanResultsRow: FC<ScanResultsRowProps> = ({ index, entry }) => {
  // Find the identifier in metadata if it exists
  return (
    <div className={clsx(styles.row)}>
      <div className={clsx(styles.id, "text-size-smaller")}>
        <Identifier preview={entry} />
      </div>
      <div className={clsx(styles.explanation, "text-size-smaller")}>
        <MarkdownDiv markdown={entry.explanation} />
      </div>
      <div className={clsx(styles.value, "text-size-smaller")}>
        <Value preview={entry} />
      </div>
    </div>
  );
};

interface IndentifierProps {
  preview: ScannerPreview;
}

const Identifier: FC<IndentifierProps> = ({ preview }): ReactNode => {
  if (preview.type === "transcript") {
    // Look in the metadata for a sample identifier
    if (
      preview.transcriptMetadata["id"] &&
      preview.transcriptMetadata["epoch"]
    ) {
      const id = String(preview.transcriptMetadata["id"]);
      const epoch = String(preview.transcriptMetadata["epoch"]);
      return `${id} (${epoch})`;
    }
  }
  return preview.transcriptSourceId;
};

interface ValueProps {
  preview: ScannerPreview;
}

// TODO: Implement popover viewer for object and list values
const Value: FC<ValueProps> = ({ preview }): ReactNode => {
  if (preview.valueType === "string") {
    return `"${String(preview.value)}"`;
  } else if (
    preview.valueType === "number" ||
    preview.valueType === "boolean"
  ) {
    return String(preview.value);
  } else if (preview.valueType === "null") {
    return "null";
  } else if (preview.valueType === "array") {
    return `[Array of length ${(preview.value as unknown[]).length}]`;
  } else if (preview.valueType === "object") {
    return `{Object with keys: ${Object.keys(preview.value as object).join(", ")}}`;
  } else {
    return "Unknown value type";
  }
};
