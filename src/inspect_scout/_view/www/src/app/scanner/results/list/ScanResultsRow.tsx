import clsx from "clsx";
import { FC } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";

import {
  getRelativePathFromParams,
  scanResultRoute,
} from "../../../../router/url";
import { useStore } from "../../../../state/store";
import { ScannerCore } from "../../../types";
import { Explanation } from "../../../values/Explanation";
import { Identifier } from "../../../values/Identifier";
import { Value } from "../../../values/Value";

import styles from "./ScanResultsRow.module.css";

interface ScanResultsRowProps {
  index: number;
  entry: ScannerCore;
}

export const ScanResultsRow: FC<ScanResultsRowProps> = ({ entry }) => {
  const params = useParams<{ "*": string }>();
  const relativePath = getRelativePathFromParams(params);
  const [searchParams] = useSearchParams();

  const setSelectedScanResult = useStore(
    (state) => state.setSelectedScanResult
  );
  const selectedScanResult = useStore((state) => state.selectedScanResult);

  // Generate the route to the scan result using the current scan path and the entry's uuid
  const isNavigable = entry.uuid !== undefined;
  const scanResultUrl = isNavigable
    ? scanResultRoute(relativePath, entry.uuid, searchParams)
    : "";

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
        <Identifier result={entry} />
      </div>
      <div className={clsx(styles.explanation, "text-size-smaller")}>
        <Explanation result={entry} />
      </div>
      <div className={clsx(styles.value, "text-size-smaller")}>
        <Value result={entry} />
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
