import clsx from "clsx";
import { FC, ReactNode } from "react";
import { Link, useParams } from "react-router-dom";

import { MarkdownDiv } from "../../../../components/MarkdownDiv";
import {
  getRelativePathFromParams,
  scanResultRoute,
} from "../../../../router/url";
import { useStore } from "../../../../state/store";
import { ScannerPreview } from "../../../types";

import styles from "./ScanResultsRow.module.css";

interface ScanResultsRowProps {
  index: number;
  entry: ScannerPreview;
}

export const ScanResultsRow: FC<ScanResultsRowProps> = ({ entry }) => {
  const params = useParams<{ "*": string }>();
  const relativePath = getRelativePathFromParams(params);

  const setSelectedScanResult = useStore(
    (state) => state.setSelectedScanResult
  );
  const selectedScanResult = useStore((state) => state.selectedScanResult);

  // Generate the route to the scan result using the current scan path and the entry's uuid
  const scanResultUrl = scanResultRoute(relativePath, entry.uuid);
  const isNavigable = entry.uuid !== undefined;

  const grid = (
    <div
      className={clsx(
        styles.row,
        !isNavigable ? styles.disabled : "",
        selectedScanResult === entry.uuid ? styles.selected : ""
      )}
      onClick={() => {
        setSelectedScanResult(entry.uuid);
      }}
    >
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

  return isNavigable ? (
    <Link to={scanResultUrl} className={clsx(styles.link)} onClick={() => {}}>
      {grid}
    </Link>
  ) : (
    grid
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
