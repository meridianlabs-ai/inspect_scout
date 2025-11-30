import clsx from "clsx";
import { has } from "markdown-it/lib/common/utils.mjs";
import { FC, memo } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";

import {
  getRelativePathFromParams,
  scanResultRoute,
} from "../../../../router/url";
import { useStore } from "../../../../state/store";
import { ScannerCore } from "../../../types";
import { Error } from "../../../values/Error";
import { Explanation } from "../../../values/Explanation";
import { Identifier } from "../../../values/Identifier";
import { ValidationResult } from "../../../values/ValidationResult";
import { Value } from "../../../values/Value";

import { GridDescriptor } from "./ScanResultsList";
import styles from "./ScanResultsRow.module.css";

interface ScanResultsRowProps {
  index: number;
  entry: ScannerCore;
  gridDescriptor: GridDescriptor;
}

const ScanResultsRowComponent: FC<ScanResultsRowProps> = ({
  entry,
  gridDescriptor,
}) => {
  // Path information
  const params = useParams<{ "*": string }>();
  const relativePath = getRelativePathFromParams(params);
  const [searchParams] = useSearchParams();

  // selected scan result
  const selectedScanResult = useStore((state) => state.selectedScanResult);
  const setSelectedScanResult = useStore(
    (state) => state.setSelectedScanResult
  );

  // Generate the route to the scan result using the current scan path and the entry's uuid
  const isNavigable = entry.uuid !== undefined;
  const scanResultUrl = isNavigable
    ? scanResultRoute(relativePath, entry.uuid, searchParams)
    : "";

  // Information about the row
  const hasExplanation = gridDescriptor.columns.includes("explanation");
  const hasLabel = gridDescriptor.columns.includes("label");
  const hasErrors = gridDescriptor.columns.includes("error");
  const hasValidations = gridDescriptor.columns.includes("validations");

  const grid = (
    <div
      style={gridDescriptor.gridStyle}
      className={clsx(
        styles.row,
        !isNavigable ? styles.disabled : "",
        selectedScanResult === entry.uuid ? styles.selected : "",
        hasExplanation ? "" : styles.noExplanation
      )}
      onClick={() => {
        if (entry.uuid) {
          setSelectedScanResult(entry.uuid);
        }
      }}
    >
      <div className={clsx(styles.id, "text-size-smaller")}>
        <Identifier result={entry} />
      </div>
      {hasExplanation && (
        <div className={clsx(styles.explanation, "text-size-smaller")}>
          <Explanation result={entry} />
        </div>
      )}
      {hasLabel && (
        <div
          className={clsx(
            styles.label,
            "text-size-smallest",
            "text-style-label",
            "text-style-secondary"
          )}
        >
          {entry.label || (
            <span className={clsx("text-style-secondary")}>—</span>
          )}
        </div>
      )}

      <div className={clsx(styles.value, "text-size-smaller")}>
        {!entry.scanError && <Value result={entry} style="inline" />}
      </div>
      {hasValidations && (
        <div className={clsx("text-size-smaller")}>
          <ValidationResult result={entry.validationResult} />
        </div>
      )}
      {hasErrors && (
        <div className={clsx(styles.error, "text-size-smallest")}>
          {entry.scanError && (
            <Error
              error={entry.scanError || "unknown error"}
              refusal={!!entry.scanErrorRefusal}
            />
          )}
        </div>
      )}
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

// memoize the component to avoid unnecessary re-renders (esp of things which may involve markdown rendering)
export const ScanResultsRow = memo(ScanResultsRowComponent);
