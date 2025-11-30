import clsx from "clsx";
import { FC, Fragment, useCallback, useRef } from "react";
import { useSearchParams } from "react-router-dom";
import { VirtuosoHandle } from "react-virtuoso";

import { LabeledValue } from "../../../components/LabeledValue";
import { LiveVirtualList } from "../../../components/LiveVirtualList";
import { updateScannerParam } from "../../../router/url";
import { useStore } from "../../../state/store";
import { Status } from "../../../types";
import { formatPercent } from "../../../utils/format";
import { ApplicationIcons } from "../../appearance/icons";
import { useSelectedScanner } from "../../hooks";

import styles from "./ScanResultsOutline.module.css";

export const ScanResultsOutline: FC = () => {
  const selectedStatus = useStore((state) => state.selectedScanStatus);
  const entries = toEntries(selectedStatus);

  const scanListHandle = useRef<VirtuosoHandle | null>(null);
  const renderRow = useCallback(
    (index: number, entry: ScanResultsOutlineEntry) => {
      return <ScanResultsRow index={index} entry={entry} />;
    },
    []
  );

  return (
    <div className={clsx(styles.container)}>
      <LiveVirtualList<ScanResultsOutlineEntry>
        id={"scans-toc-list"}
        listHandle={scanListHandle}
        data={entries}
        renderRow={renderRow}
      />
    </div>
  );
};

const ScanResultsRow: FC<{ index: number; entry: ScanResultsOutlineEntry }> = ({
  index,
  entry,
}) => {
  const selectedScanner = useSelectedScanner();
  const setSelectedScanner = useStore((state) => state.setSelectedScanner);
  const [searchParams, setSearchParams] = useSearchParams();
  const handleClick = useCallback(
    (title: string) => {
      setSelectedScanner(title);
      setSearchParams(updateScannerParam(searchParams, title), {
        replace: true,
      });
    },
    [setSelectedScanner, searchParams, setSearchParams]
  );

  return (
    <div
      className={clsx(
        styles.entry,
        selectedScanner === entry.title ? styles.selected : ""
      )}
      key={index}
      onClick={() => {
        handleClick(entry.title);
      }}
    >
      <div className={clsx(styles.titleBlock)}>
        <div className={clsx("text-size-large", styles.title)}>
          {entry.title}
        </div>
        {entry.params && entry.params.length > 0 && (
          <div className={clsx("text-size-smallest", styles.subTitle)}>
            {entry.params.join("")}
          </div>
        )}
      </div>

      <LabeledValue
        label="Results"
        layout="row"
        className={clsx("text-size-smallest")}
      >
        {entry.results}
      </LabeledValue>

      {!!entry.errors && (
        <LabeledValue
          label="Errors"
          layout="row"
          className={clsx("text-size-smallest")}
        >
          {entry.errors}
        </LabeledValue>
      )}

      {entry.validations !== undefined && (
        <LabeledValue
          label="Validations"
          layout={typeof entry.validations === "number" ? "row" : "column"}
          className={clsx("text-size-smallest")}
        >
          {typeof entry.validations === "number" ? (
            formatPercent(entry.validations)
          ) : (
            <ValidationTable validations={entry.validations} />
          )}
        </LabeledValue>
      )}
    </div>
  );
};

interface ScanResultsOutlineEntry {
  icon?: string;
  title: string;
  tokens?: number;
  results: number;
  scans: number;
  validations?: number | Record<string, number>;
  errors?: number;
  params?: string[];
}

const toEntries = (status?: Status): ScanResultsOutlineEntry[] => {
  if (!status) {
    return [];
  }
  const entries: ScanResultsOutlineEntry[] = [];
  for (const scanner of Object.keys(status.summary.scanners)) {
    // The summary
    const summary = status.summary.scanners[scanner];

    // The configuration
    const scanInfo = status.spec.scanners[scanner];

    const formattedParams: string[] = [];
    if (scanInfo) {
      const params = scanInfo.params || {};
      for (const [key, value] of Object.entries(params)) {
        formattedParams.push(`${key}=${JSON.stringify(value)}`);
      }
    }

    const validations = summary?.validations
      ? resolveValidations(summary.validations)
      : undefined;

    entries.push({
      icon: ApplicationIcons.scorer,
      title: scanner,
      results: summary?.results || 0,
      scans: summary?.scans || 0,
      tokens: summary?.tokens,
      errors: summary?.errors,
      params: formattedParams,
      validations: validations,
    });
  }
  return entries;
};

const resolveValidations = (
  validations: Array<boolean | Record<string, boolean>>
): number | Record<string, number> | undefined => {
  if (validations.length === 0) {
    return undefined;
  }

  const first = validations[0];
  if (typeof first === "boolean") {
    // Count number of true values
    const correct = validations.reduce((count, v) => count + (v ? 1 : 0), 0);
    const total = validations.length;
    return correct / total;
  } else {
    // Count per key
    const counts: Record<string, number> = {};
    const total = validations.length;
    for (const validation of validations) {
      if (typeof validation === "object") {
        for (const [key, value] of Object.entries(validation)) {
          if (value) {
            counts[key] = (counts[key] || 0) + 1;
          }
        }
      }
    }

    // Compute percentages
    for (const key of Object.keys(counts)) {
      counts[key] = (counts[key] || 0) / total;
    }
    return counts;
  }
};

const ValidationTable: FC<{
  validations: Record<string, number>;
}> = ({ validations }) => {
  return (
    <div className={clsx(styles.validationTable)}>
      {Object.entries(validations).map(([key, value]) => (
        <Fragment key={key}>
          <div className={clsx(styles.validationKey)}>{key}</div>
          <div className={clsx(styles.validationValue)}>
            {formatPercent(value)}
          </div>
        </Fragment>
      ))}
    </div>
  );
};
